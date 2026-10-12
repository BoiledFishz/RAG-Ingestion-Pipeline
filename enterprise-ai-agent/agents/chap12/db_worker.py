"""Database Query Worker: registered, parameterized, read-only queries over the sample snapshot.

There is no Text-to-SQL. Users, prompts and plans choose only an operation name and typed
parameters; SQL text is owned by this module. Every query is restricted to the caller's
authorized product IDs and bounded by a statement deadline and a result-size cap.
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.chap12.budget import Budget, BudgetExhausted
from agents.chap12.contracts import (
    DbInput,
    DbPayload,
    DbRow,
    TrustedContext,
    WorkerError,
    WorkerResult,
)

MAX_GROUP_ROWS = 40
# Product inference, chosen on the tune split only (evaluation/chap12_retrieval_tune.py):
# the product tagged on >= 60% of the top-3 BM25 documents of the question.
INFER_TOP_K = 3
INFER_MIN_SHARE = 0.6
INFER_OVERFETCH = 200
INFERENCE_LIMITATION = (
    "问题未写明目录中的产品名；产品由问题在样本库中 BM25 前 3 篇文档的官方产品标注推断"
    "（至少 2 篇一致），可能不是提问者所指产品。")
LIMITATIONS = [
    "计数口径：本次样本快照（随机抽取的 TechQA 训练题的官方候选文档并集）中，官方 metadata "
    "的 productId 与条件匹配的不同文档数；不是 IBM 全量知识库，也不是工单量、故障率或用户数。",
    "日期为官方 metadata 中的文档日期，不等于问题发生时间或产品发布时间。",
    "文档类别按官方文档 ID 前缀推断（swg1=APAR，swg27=产品文档，其余 swg2=Technote）。",
]

# Program-owned templates; `?` parameters only. The product filter is always applied.
SOURCE = "technotes t JOIN document_products p ON p.doc_id = t.doc_id"
FILTER = ("p.product_id = ? AND (? IS NULL OR t.published_date >= ?) "
          "AND (? IS NULL OR t.published_date <= ?) AND (? IS NULL OR t.doc_class = ?)")
TEMPLATES = {
    "count_documents": f"SELECT count(DISTINCT t.doc_id) FROM {SOURCE} WHERE {FILTER}",
    "count_by_year": (
        f"SELECT substr(t.published_date, 1, 4) AS year, count(DISTINCT t.doc_id) FROM {SOURCE} "
        f"WHERE {FILTER} AND t.published_date IS NOT NULL GROUP BY year ORDER BY year LIMIT ?"),
    "list_recent_documents": (
        f"SELECT DISTINCT t.doc_id, t.title, t.published_date FROM {SOURCE} WHERE {FILTER} "
        "ORDER BY t.published_date DESC, t.doc_id LIMIT ?"),
}


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str


class Catalog:
    """Official product names in the snapshot, used for deterministic slot resolution."""

    def __init__(self, products: list[Product]) -> None:
        self.by_id = {p.product_id: p for p in products}
        self.by_name = {p.name.casefold(): p for p in products}
        aliases: dict[str, Product] = {}
        for product in products:
            if product.name == product.product_id:
                continue
            for alias in self._aliases(product.name):
                aliases.setdefault(alias, product)
        self.aliases = sorted(aliases.items(), key=lambda item: -len(item[0]))

    @staticmethod
    def _aliases(name: str) -> set[str]:
        base = name.strip()
        variants = {base, re.sub(r"^IBM\s+", "", base)}
        variants |= {re.sub(r"\s+V?\d+(\.\d+)*$", "", v) for v in set(variants)}
        # Single short tokens such as "MQ" are kept only when written in capitals.
        return {v for v in variants if len(v) >= 4 or (len(v) >= 2 and v.isupper())}

    def lookup(self, value: str) -> Product | None:
        return self.by_id.get(value) or self.by_name.get(value.casefold())

    def find(self, text: str) -> list[Product]:
        """Products named in text, in textual order; longest alias wins, no overlaps."""
        taken: list[tuple[int, int]] = []
        found: list[tuple[int, Product]] = []
        for alias, product in self.aliases:
            flags = re.IGNORECASE if " " in alias else 0
            for match in re.finditer(r"(?<![\w/])" + re.escape(alias) + r"(?![\w/])", text,
                                     flags):
                span = match.span()
                if any(span[0] < end and start < span[1] for start, end in taken):
                    continue
                taken.append(span)
                found.append((span[0], product))
        ordered: list[Product] = []
        for _, product in sorted(found, key=lambda item: item[0]):
            if product not in ordered:
                ordered.append(product)
        return ordered


class DatabaseQueryWorker:
    name = "database"

    def __init__(self, path: Path, *, statement_timeout: float = 10.0,
                 max_retries: int = 1) -> None:
        self.path = path.resolve()
        if not self.path.is_file():
            raise FileNotFoundError(f"Sample index not found: {self.path}")
        self.statement_timeout, self.max_retries = statement_timeout, max_retries
        with self.connect(time.monotonic() + 30) as db:
            manifest = dict(db.execute("SELECT key, value FROM manifest"))
            if manifest.get("complete") != "true":
                raise ValueError("sample index is incomplete")
            # Names come only from documents tagged with exactly one product ID.
            rows = db.execute(
                "SELECT product_id, product_name, count(*) FROM technotes "
                "WHERE product_id IS NOT NULL AND product_name IS NOT NULL "
                "AND instr(product_id, ',') = 0 "
                "GROUP BY product_id, product_name ORDER BY product_id, 3 DESC, product_name"
            ).fetchall()
            ids = [r[0] for r in db.execute(
                "SELECT DISTINCT product_id FROM document_products ORDER BY product_id")]
        from rag.techqa.index import TechQAIndex

        self.index = TechQAIndex(self.path)
        self.snapshot = (f"{manifest['scope']}:seed={manifest.get('seed')}:"
                         f"docs={manifest['document_count']}")
        names: dict[str, str] = {}
        for product_id, name, _ in rows:
            names.setdefault(product_id, name)  # most frequent official name per product ID
        # IDs seen only in multi-product documents stay addressable by ID (name = ID).
        self.catalog = Catalog([Product(i, names.get(i, i)) for i in ids])

    @contextmanager
    def connect(self, deadline: float) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=2,
                             check_same_thread=False)
        try:
            db.execute("PRAGMA query_only = ON")
            # Abort the running statement once the deadline passes (SQLITE_INTERRUPT).
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            yield db
        finally:
            db.close()

    def _result(self, run_id: str, task_id: str, status: str, *, payload: DbPayload | None = None,
                error: WorkerError | None = None, started: float, budget: Budget,
                retries: int = 0) -> WorkerResult:
        return WorkerResult.model_validate({
            "run_id": run_id, "task_id": task_id, "worker": self.name, "status": status,
            "payload": payload, "error": error, "limitations": list(LIMITATIONS),
            "usage": {"db_queries": budget.worker_count(self.name, "db"),
                      "tool_calls": budget.worker_count(self.name, "tool"), "retries": retries,
                      "elapsed_ms": (time.monotonic() - started) * 1000},
        })

    async def run(self, run_id: str, task_id: str, request: DbInput, ctx: TrustedContext,
                  budget: Budget) -> WorkerResult:
        started = time.monotonic()

        def fail(status: str, category: str, message: str, retryable: bool = False,
                 retries: int = 0) -> WorkerResult:
            return self._result(run_id, task_id, status, started=started, budget=budget,
                                retries=retries, error=WorkerError.model_validate(
                                    {"category": category, "message": message,
                                     "retryable": retryable}))

        if self.name not in ctx.allowed_workers or request.operation not in \
                ctx.allowed_db_operations:
            return fail("permission_denied", "permission_denied",
                        f"operation {request.operation} is not authorized")
        try:
            budget.reserve("tool", self.name)
        except BudgetExhausted as exc:
            return fail("failed", "budget_exhausted", str(exc))
        reference, source = request.product, request.product_source
        evidence: list[str] = []
        if reference is None and request.infer_product and request.query:
            try:
                budget.reserve("db", self.name)
            except BudgetExhausted as exc:
                return fail("failed", "budget_exhausted", str(exc))
            reference, evidence = await asyncio.to_thread(self._infer, request.query, ctx)
            source = "inferred"
        if reference is None:
            # Missing input is not an execution failure: nothing publishable, ask the user.
            return fail("no_data", "clarification_required",
                        "no catalogue product identified; specify data_request.product")
        product = self.catalog.lookup(reference)
        if product is None:
            return fail("failed", "invalid_input", "product is not in the snapshot catalogue")
        if not ctx.product_allowed(product.product_id):
            # Same message whether or not data exists: no existence leak.
            return fail("permission_denied", "permission_denied",
                        "product scope is not authorized")

        start = request.date_from.isoformat() if request.date_from else None
        end = request.date_to.isoformat() if request.date_to else None
        params: list[Any] = [product.product_id, start, start, end, end,
                             request.doc_class, request.doc_class]
        limit = MAX_GROUP_ROWS + 1 if request.operation == "count_by_year" else request.limit + 1
        if request.operation != "count_documents":
            params.append(limit)
        sql = TEMPLATES[request.operation]

        retries = 0
        rows: list[tuple[Any, ...]] = []
        while True:
            try:
                budget.reserve("db", self.name)
            except BudgetExhausted as exc:
                return fail("failed", "budget_exhausted", str(exc), retries=retries)
            deadline = time.monotonic() + min(self.statement_timeout, budget.remaining())
            try:
                rows = await asyncio.to_thread(self._execute, sql, params, deadline)
                break
            except sqlite3.OperationalError as exc:
                text = str(exc).lower()
                if "interrupt" in text:
                    return fail("timeout", "timeout", "statement deadline exceeded",
                                retries=retries)
                transient = "locked" in text or "busy" in text
                if transient and retries < self.max_retries:
                    retries += 1
                    continue
                return fail("failed", "dependency_unavailable",
                            "database unavailable" if transient else "database error",
                            retryable=transient, retries=retries)
            except sqlite3.DatabaseError:
                return fail("failed", "dependency_unavailable", "database error",
                            retries=retries)

        payload: dict[str, Any] = {
            "operation": request.operation, "product_name": product.name,
            "product_id": product.product_id, "product_source": source,
            "inference_doc_ids": evidence, "date_from": start, "date_to": end,
            "doc_class": request.doc_class, "unit": "documents", "snapshot": self.snapshot,
            "query_template": request.operation,
        }
        status = "completed"
        if request.operation == "count_documents":
            payload |= {"metric": "distinct documents matching filters", "count": rows[0][0]}
            empty = rows[0][0] == 0
        elif request.operation == "count_by_year":
            truncated = len(rows) > MAX_GROUP_ROWS
            rows = rows[:MAX_GROUP_ROWS]
            payload |= {"metric": "distinct documents per metadata year",
                        "rows": [DbRow(key=str(y), value=int(c)) for y, c in rows],
                        "count": sum(int(c) for _, c in rows), "truncated": truncated}
            empty, status = not rows, "partial" if truncated else "completed"
        else:
            truncated = len(rows) > request.limit
            rows = rows[:request.limit]
            payload |= {"metric": f"most recent documents (max {request.limit})",
                        "rows": [DbRow(key=str(d), value=f"{d2 or 'undated'} | {t}")
                                 for d, t, d2 in rows], "truncated": truncated}
            empty = not rows
        result = self._result(run_id, task_id, "no_data" if empty else status,
                              payload=DbPayload.model_validate(payload), started=started,
                              budget=budget, retries=retries)
        if source == "inferred":
            result.limitations.insert(0, INFERENCE_LIMITATION)
        return result

    def _infer(self, query: str, ctx: TrustedContext) -> tuple[str | None, list[str]]:
        """Infer only among documents the caller may see, so a denial can never reveal
        which unauthorized product the question resembles."""
        with self.connect(time.monotonic() + self.statement_timeout) as db:
            if "*" in ctx.allowed_product_ids:
                hits = self.index.search(query, INFER_TOP_K)
            else:
                hits = [d for d in self.index.search(query, INFER_OVERFETCH)
                        if any(ctx.product_allowed(p) for p in self._products(db, d["id"]))]
            docs = [d["id"] for d in hits[:INFER_TOP_K]]
            if not docs:
                return None, []
            marks = ",".join("?" * len(docs))
            rows = [r for r in db.execute(
                f"SELECT product_id, count(*) FROM document_products WHERE doc_id IN ({marks}) "
                "GROUP BY product_id ORDER BY 2 DESC, product_id", docs).fetchall()
                if ctx.product_allowed(str(r[0]))]
        if rows and rows[0][1] / len(docs) >= INFER_MIN_SHARE:
            return str(rows[0][0]), docs
        return None, []

    @staticmethod
    def _products(db: sqlite3.Connection, doc: str) -> list[str]:
        return [r[0] for r in db.execute(
            "SELECT product_id FROM document_products WHERE doc_id = ?", (doc,))]

    def _execute(self, sql: str, params: list[Any], deadline: float) -> list[tuple[Any, ...]]:
        with self.connect(deadline) as db:
            return list(db.execute(sql, params).fetchall())
