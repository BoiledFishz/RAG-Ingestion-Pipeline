"""Full authorized TechQA distinct-document statistics; no model or RAG needed."""

from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from agents.project2.budget import Budget, BudgetExceeded
from agents.project2.policy import TrustedContext
from models.project2 import AnalysisRequest, WorkerResult

LOGGER = logging.getLogger(__name__)
ARCHIVE = "6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118"
ENTITY = re.compile(r"WebSphere\s+Application\s+Server|WebSphere\s+Message\s+Broker|IBM\s+Integration\s+Bus|WebSphere\s+MQ|IBM\s+HTTP\s+Server|WebSphere\s+Portal|Netcool\/Impact|Netcool|DataPower|ClearQuest|Datacap|Cognos|SPSS|DB2|BPM|MQ|Impact|Rational|CICS|Tivoli|FileNet|PureApplication|Passport\s+Advantage|Fix\s+Central|UCD|RDz|ITNM|ITM|Nokia\s+NSP", re.I | re.ASCII)
VERSION = re.compile(r"\b(?:V(?:ersion)?\s*\d+(?:\.\d+)*|Release\s*\d+|\d+\.\d+(?:\.\d+)*)\b", re.I | re.ASCII)
PLATFORM = re.compile(r"\bz\/OS\b|\b(?:Windows|Linux|AIX|UNIX|Solaris|macOS|Mac|NonStop|RedHat|RHEL)\b", re.I | re.ASCII)
# Query-side literal component names: acronyms and internal-capital names.
# No alias expansion or official-answer/document lookup. This fallback is
# deliberately limited to a missing known entity, keeping existing predicates.
COMPONENT = re.compile(r"\b(?:[A-Z]{2,12}|[A-Z][a-z]+(?:[A-Z][A-Za-z]*)+|[A-Z][a-z]+(?=\s+(?:(?:[Vv](?:ersion)?|Release)\s*)?\d))\b", re.ASCII)
NON_COMPONENT = frozenset({"ERROR", "WARNING", "INFO", "ANSWER", "QUESTION", "HTTP", "HTTPS", "URL", "SQL", "XML", "IP", "ID", "QID", "SSL", "INSTALLATION", "EXIT", "REQUESTED", "TERMINATION", "REASON", "CODE", "API", "NET"})
URL = re.compile(r"\b(?:[a-z][a-z0-9+.-]*://|www\.)\S+", re.I | re.ASCII)
REQUEST_SLOTS_VERSION = "request-slots-v1.3-url-exclusion"
LIMITATIONS = [
    "文档数是词项匹配的知识库覆盖计数，不是工单量、故障率、用户数、产品使用量或销售指标。",
    "包含产品/版本词项不证明该版本受支持、受影响或适用于用户；技术适用性由RAG依据原文解释。",
    "同一文档可命中两个比较组；tokenizer的词干和标点处理可能扩大字面匹配。",
    "统计只覆盖明确授权的数据快照；示例文档为有限行，不代表完整清单。",
]


def query_groups(request: AnalysisRequest) -> list[list[str]]:
    if request.analysis_predicates is not None:
        groups = request.analysis_predicates
        if len(groups) != (2 if request.analysis_operation == "compare_document_counts" else 1):
            raise ValueError("clarification_required:predicate_group_count")
        return groups
    # URL path/version fragments are source locations, not product slots.
    # The length-preserving view retains every original span and leaves the
    # actual request and RAG input byte-for-byte unchanged.
    slot_text = URL.sub(lambda match: " " * len(match.group()), request.query)
    entities = list(ENTITY.finditer(slot_text))
    if not entities:
        entities = [match for match in COMPONENT.finditer(slot_text)
                    if match.group() not in NON_COMPONENT]
    if not entities:
        raise ValueError("clarification_required:entity")
    pairs: list[list[str]] = []
    for index, entity in enumerate(entities):
        end = min(entity.end()+32, entities[index+1].start() if index+1 < len(entities) else len(slot_text))
        version = VERSION.search(slot_text, entity.end(), end)
        if version and not re.search(r"\b(?:IP|XML)\b", slot_text[max(0, version.start()-15):version.start()], re.I):
            group = [entity.group(), version.group()]
            if tuple(x.casefold() for x in group) not in {tuple(x.casefold() for x in p) for p in pairs}:
                pairs.append(group)
    if request.analysis_operation == "compare_document_counts":
        if len(pairs) < 2:
            # A known product must not hide another literal component in the
            # same request. Preserve already valid pairs; no aliases or gold.
            extras=[m for m in COMPONENT.finditer(slot_text) if m.group() not in NON_COMPONENT
                    and not any(m.start()<e.end() and e.start()<m.end() for e in entities)]
            expanded=sorted([*entities,*extras],key=lambda m:m.start())
            for index,entity in enumerate(expanded):
                end=min(entity.end()+32,expanded[index+1].start() if index+1<len(expanded) else len(slot_text))
                version=VERSION.search(slot_text,entity.end(),end)
                if version and not re.search(r"\b(?:IP|XML)\b",slot_text[max(0,version.start()-15):version.start()],re.I):
                    group=[entity.group(),version.group()]
                    if tuple(x.casefold() for x in group) not in {tuple(x.casefold() for x in p) for p in pairs}:pairs.append(group)
            if len(pairs)<2:raise ValueError("clarification_required:two_entity_version_pairs")
        return pairs[:2]
    first = entities[0].group()
    group = next((p for p in pairs if p[0].casefold() == first.casefold()), [first])
    platform = PLATFORM.search(slot_text)
    return [[*group, platform.group()]] if platform else [group]


def fts(phrases: list[str]) -> str:
    return " AND ".join('"' + phrase.replace('"', '""') + '"' for phrase in phrases)


class DatabaseWorker:
    def __init__(self, path: Path, *, inject_timeout_group: int | None = None) -> None:
        self.path = path.resolve()
        self.inject_timeout_group = inject_timeout_group

    async def run(self, request: AnalysisRequest, context: TrustedContext, budget: Budget, run_id: str) -> WorkerResult:
        result = WorkerResult(run_id=run_id, task_id="techqa_document_query", worker="database", status="failed", limitations=LIMITATIONS,
                              payload={"groups": [], "intersection": None, "delta_a_minus_b": None, "measurement_complete": False, "unit": "original_document"})
        if not context.permits(request.analysis_operation):
            result.status, result.error = "permission_denied", {"category": "permission_denied", "retryable": False}
            result.usage = budget.snapshot()
            return result
        try:
            groups = query_groups(request)
            result.payload["groups"] = [{"predicate": group, "count": None, "samples": []} for group in groups]
            # The SQL callback observes the same cancellation flag as the API.
            await asyncio.wait_for(asyncio.to_thread(self._execute, request, groups, budget, result), budget.remaining(25))
        except (BudgetExceeded, TimeoutError) as exc:
            if isinstance(exc, TimeoutError) and not isinstance(exc, BudgetExceeded):
                budget.cancel()
            completed = any(g["count"] is not None for g in result.payload["groups"])
            result.status = "partial" if completed else "timeout"
            result.error = {"category": str(exc) or "database_timeout", "retryable": False}
            LOGGER.warning("Database request=%s status=%s timeout=%s", run_id, result.status, exc)
        except (ValueError, sqlite3.Error, OSError) as exc:
            result.status = "failed"
            category = "data_version_mismatch" if "data_version_mismatch" in str(exc) else "clarification_required" if "clarification_required" in str(exc) else "database_error"
            result.error = {"category": category, "retryable": False, "detail": str(exc)[:200]}
            LOGGER.warning("Database request=%s error=%s", run_id, category)
        result.usage = budget.snapshot()
        return result

    def _execute(self, request: AnalysisRequest, groups: list[list[str]], budget: Budget, result: WorkerResult) -> None:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        db = sqlite3.connect(self.path.as_uri()+"?mode=ro", uri=True, timeout=min(12, budget.remaining()))
        started = time.monotonic()
        statement_started = started

        def execute(sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
            nonlocal statement_started
            budget.reserve("db")
            statement_started = time.monotonic()
            return db.execute(sql, parameters)

        def interrupted() -> int:
            return int(budget.cancelled or time.monotonic() >= budget.deadline or time.monotonic()-started >= 25 or time.monotonic()-statement_started >= 12)

        db.set_progress_handler(interrupted, 1000)
        try:
            manifest = dict(execute("SELECT key,value FROM manifest"))
            schema = execute("SELECT sql FROM sqlite_master WHERE name='search'").fetchone()
            if (manifest.get("scope") != "full" or manifest.get("complete") != "true" or manifest.get("format_version") != "1"
                    or manifest.get("source_archive_sha256") != ARCHIVE or not schema or "tokenize='porter unicode61'" not in schema[0]):
                raise ValueError("data_version_mismatch")
            result.payload["data_version"] = manifest
            result.payload["rules_version"] = "techqa-fts-predicate-v1"
            result.payload["request_slots_version"] = REQUEST_SLOTS_VERSION
            result.payload["operation"] = request.analysis_operation
            for index, group in enumerate(groups):
                if index == self.inject_timeout_group:
                    budget.reserve("db")
                    raise BudgetExceeded("injected_database_group_timeout")
                phrase = fts(group)
                value = execute("SELECT COUNT(DISTINCT docs.doc_id) FROM search JOIN docs ON docs.rowid=search.rowid WHERE search MATCH ?", (phrase,)).fetchone()[0]
                result.payload["groups"][index]["count"] = value
                if request.include_samples and request.sample_limit:
                    samples = execute("SELECT docs.doc_id,docs.title FROM search JOIN docs ON docs.rowid=search.rowid WHERE search MATCH ? ORDER BY docs.doc_id LIMIT ?", (phrase, request.sample_limit)).fetchall()
                    result.payload["groups"][index]["samples"] = [{"doc_id": row[0], "title": row[1]} for row in samples]
                result.evidence.append({"source_id": f"Q{index+1}", "predicate": group, "count": value, "scope": "full", "measurement_complete": True})
            if len(groups) == 2:
                overlap = execute("SELECT COUNT(*) FROM (SELECT docs.doc_id FROM search JOIN docs ON docs.rowid=search.rowid WHERE search MATCH ? INTERSECT SELECT docs.doc_id FROM search JOIN docs ON docs.rowid=search.rowid WHERE search MATCH ?)", (fts(groups[0]), fts(groups[1]))).fetchone()[0]
                result.payload["intersection"] = overlap
                result.payload["delta_a_minus_b"] = result.payload["groups"][0]["count"]-result.payload["groups"][1]["count"]
            result.payload["measurement_complete"] = True
            result.payload["samples_truncated"] = any(g["count"] > len(g["samples"]) for g in result.payload["groups"])
            result.status = "completed" if any(g["count"] for g in result.payload["groups"]) else "no_data"
            LOGGER.info("Database request=%s status=%s counts=%s", result.run_id, result.status, [g["count"] for g in result.payload["groups"]])
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc):
                raise BudgetExceeded("database_statement_timeout") from exc
            raise
        finally:
            db.close()
