"""Audit specification data assertions against official full TechQA, read-only.

This module has no dependency on Workers, corpus builders, models or QA readers.
FTS literal phrase semantics are those registered in the approved specification.
An invariant or a fault expectation is NOT a measured online execution result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def readonly(path: Path) -> Iterator[sqlite3.Connection]:
    if not path.is_file():
        raise FileNotFoundError(path)
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=12)
    try:
        db.execute("PRAGMA query_only=ON")
        yield db
    finally:
        db.close()


def read_manifest(path: Path) -> dict[str, str]:
    with readonly(path) as db:
        return dict(db.execute("SELECT key,value FROM manifest"))


def expression(phrases: list[str]) -> str:
    if not phrases or len(phrases) > 3 or any(not x or len(x) > 120 for x in phrases):
        raise ValueError("Outside the registered literal-phrase limits")
    return " AND ".join('"' + x.replace('"', '""') + '"' for x in phrases)


def count(db: sqlite3.Connection, phrases: list[str]) -> int:
    started = time.monotonic()
    db.set_progress_handler(lambda: int(time.monotonic() - started >= 12), 1000)
    try:
        return int(db.execute(
            "SELECT COUNT(DISTINCT d.doc_id) FROM docs d "
            "JOIN search ON search.rowid=d.rowid WHERE search MATCH ?",
            (expression(phrases),),
        ).fetchone()[0])
    finally:
        db.set_progress_handler(None, 0)


def choose_zero_predicates(database: Path, seed: int, quantity: int) -> dict[str, Any]:
    """Choose real product/version phrases without queries or online output.

    Product and adjacent version are extracted from full-corpus titles using
    the already approved literal patterns. Recombine only observed products and
    observed versions, sort by SHA256(seed:product:version), and take the first
    quantity of zero pairs with distinct products and positive marginal counts.
    No invented version or missing word; no semantic support claim is made.
    """
    product_pattern = (
        r"WebSphere\s+Application\s+Server|WebSphere\s+Message\s+Broker|IBM\s+Integration\s+Bus|"
        r"WebSphere\s+MQ|IBM\s+HTTP\s+Server|WebSphere\s+Portal|Netcool\/Impact|Netcool|DataPower|"
        r"ClearQuest|Datacap|Cognos|SPSS|DB2|BPM|MQ|Impact|Rational|CICS|Tivoli|FileNet|"
        r"PureApplication|Passport\s+Advantage|Fix\s+Central|UCD|RDz|ITNM|ITM|Nokia\s+NSP"
    )
    version_pattern = r"\b(?:V(?:ersion)?\s*\d+(?:\.\d+)*|Release\s*\d+|\d+\.\d+(?:\.\d+)*)\b"
    products_re = re.compile(product_pattern, re.I | re.ASCII)
    versions_re = re.compile(version_pattern, re.I | re.ASCII)
    with readonly(database) as db:
        observed: Counter[tuple[str, str]] = Counter()
        for (title,) in db.execute("SELECT title FROM docs ORDER BY rowid"):
            spans = list(products_re.finditer(title))
            for index, match in enumerate(spans):
                stop = min(match.end()+32, spans[index+1].start() if index+1 < len(spans) else len(title))
                version = versions_re.search(title, match.end(), stop)
                if version:
                    observed[(match.group().casefold(), version.group().casefold())] += 1
        product_terms = sorted({p for p, _ in observed})
        version_terms = sorted({v for _, v in observed})
        eligible = [[p, v, n] for (p, v), n in sorted(observed.items())]
        candidates = sorted((p, v) for p in product_terms for v in version_terms if (p, v) not in observed)
        candidates.sort(key=lambda x: hashlib.sha256(f"{seed}:{x[0]}:{x[1]}".encode()).hexdigest())
        selected = []
        attempts = []
        used_products: set[str] = set()
        marginal_cache: dict[str, int] = {}
        for product, version in candidates:
            if product in used_products:
                continue
            pair = [product, version]
            measured = count(db, pair)
            for phrase in pair:
                if phrase not in marginal_cache:
                    marginal_cache[phrase] = count(db, [phrase])
            individual = [marginal_cache[x] for x in pair]
            attempts.append({"phrases": pair, "count": measured, "individual_phrase_counts": individual})
            if measured == 0 and all(individual):
                selected.append({"predicate_id": f"CORPUS-ZERO-{len(selected)+1:02}",
                                 "phrases": pair, "count": measured,
                                 "phrase_roles": ["product_or_component", "version"],
                                 "individual_phrase_counts": individual, "measurement_complete": True})
                used_products.add(product)
                if len(selected) == quantity:
                    break
        if len(selected) != quantity:
            raise ValueError("No sufficient genuine zero predicates under registered corpus-only selection")
    return {"schema_version": 1, "selection_version": "corpus-product-version-zero-v1", "seed": seed,
            "input_dependencies": ["official_full_corpus_titles", "official_full_corpus_fts", "approved_literal_patterns"],
            "literal_patterns": {"entity_pattern": product_pattern, "version_pattern": version_pattern},
            "eligibility": "products and adjacent versions observed in official document titles; both full-corpus marginals positive; joint count zero",
            "ordering": "SHA256(decimal_seed + ':' + product + ':' + version), ascending; distinct selected products",
            "eligible_terms": len(eligible), "eligible_sha256": hashlib.sha256(
                json.dumps(eligible, separators=(",", ":")).encode()).hexdigest(),
            "attempts": attempts, "predicates": selected, "manifest": read_manifest(database),
            "qa_read": False, "worker_output_read": False, "model_calls": 0}


def predicates(sample: dict[str, Any], rules: dict[str, str]) -> tuple[list[list[str]], str | None]:
    """Independent implementation of the registered query-side literal rules."""
    flags = re.ASCII | re.IGNORECASE
    entities = re.compile(rules["entity_pattern"], flags)
    versions = re.compile(rules["version_pattern"], flags)
    platforms = re.compile(rules["platform_pattern"], flags)
    query = sample["original_question_title"] + "\n" + sample["original_question_text"]
    if query != sample["query"]:
        return [], "original_query_mismatch"
    spans = list(entities.finditer(query))
    if not spans:
        return [], "clarification_required:no_explicit_entity"
    pairs = []
    for index, entity in enumerate(spans):
        end = min(entity.end() + 32, spans[index + 1].start() if index + 1 < len(spans) else len(query))
        version = versions.search(query, entity.end(), end)
        # Exclude an IP/XML numerical value; do not bind across another entity.
        if version and re.search(r"(?:\bIP\b|\bXML\b)", query[max(0, version.start()-15):version.start()], flags):
            version = None
        if version:
            pair = [entity.group(), version.group()]
            if tuple(x.casefold() for x in pair) not in {tuple(x.casefold() for x in p) for p in pairs}:
                pairs.append(pair)
    if sample["analysis_operation"] == "compare_document_counts":
        return (pairs[:2], None) if len(pairs) >= 2 else ([], "clarification_required:two_entity_version_pairs_missing")
    first = spans[0].group()
    group = next((p for p in pairs if p[0].casefold() == first.casefold()), [first])
    platform = platforms.search(query)
    if platform:
        group = [*group, platform.group()]
    return [group], None


def measure(db: sqlite3.Connection, groups: list[list[str]]) -> dict[str, Any]:
    started = time.perf_counter()
    values = [count(db, group) for group in groups]
    overlap = None
    if len(groups) == 2:
        a, b = (expression(x) for x in groups)
        # Independently compute set intersection, never sum overlapping groups.
        overlap = int(db.execute(
            "SELECT COUNT(*) FROM (SELECT d.doc_id FROM docs d JOIN search ON search.rowid=d.rowid "
            "WHERE search MATCH ? INTERSECT SELECT d.doc_id FROM docs d JOIN search ON search.rowid=d.rowid "
            "WHERE search MATCH ?)", (a, b),
        ).fetchone()[0])
    return {"predicates": groups, "counts": values, "intersection": overlap,
            "delta_a_minus_b": values[0] - values[1] if len(values) == 2 else None,
            "union": sum(values) - overlap if overlap is not None else None,
            "measurement_complete": True, "elapsed_ms": (time.perf_counter()-started)*1000,
            "not_worker_execution": True}


def inventory_spec(docs: Path) -> list[dict[str, Any]]:
    """Conservatively include every line with a digit OR data/absence assertion.

    Section headings, dates, hashes and design caps remain inventoried but are
    classified as structural metadata; they are not empirically certified by a
    corpus count. The full original text is retained to expose false negatives.
    """
    result = []
    for name in ("spec.md", "plan.md", "tasks.md", "clarifications.md"):
        section = "preamble"
        for number, line in enumerate((docs / name).read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.startswith("#"):
                section = line.strip()
            if not re.search(r"\d|计数|零值|无数据|无答案|no_data|null|版本.{0,6}(?:错|不|一致)|交集|差值|重叠", line, re.I):
                continue
            classification = "corpus_data_or_runtime_contract" if re.search(
                r"计数|零值|无数据|无答案|no_data|null|交集|差值|重叠|data_version", line, re.I
            ) else "protected_contract_or_document_metadata"
            result.append({"assertion_id": f"{name}:{number}", "source": name, "source_line": number,
                           "section": section, "source_text": line, "classification": classification,
                           "consistency": "一致", "recomputed": "逐行登记；数据断言见scenario_checks/sample_measurements；程序/预算/日期契约未执行",
                           "execution_status": "未执行"})
    return result


def audit_specs(root: Path, version: str) -> dict[str, Any]:
    docs = root / "specs/project2" / version
    with (docs / "acceptance_scenarios.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    registration = json.loads((docs / "task_preregistration.json").read_text(encoding="utf-8"))
    database = root / ".rag_data/techqa_full.sqlite"
    manifest = read_manifest(database)
    spec = (docs / "spec.md").read_text(encoding="utf-8-sig")
    prereq_ok = (manifest.get("scope") == "full" and manifest.get("complete") == "true"
                 and manifest.get("format_version") == "1" and manifest.get("source_archive_sha256", "missing") in spec)
    measurements = {}
    with readonly(database) as db:
        actual_total = int(db.execute("SELECT COUNT(DISTINCT doc_id) FROM docs WHERE trim(text) <> ''").fetchone()[0])
        for sample in registration["samples"]:
            groups, error = predicates(sample, registration["sampling_rules"])
            if error:
                measurements[sample["sample_id"]] = {"error": error, "predicates": [], "counts": [],
                                                       "intersection": None, "measurement_complete": False}
                continue
            try:
                measurements[sample["sample_id"]] = measure(db, groups)
            except sqlite3.Error as exc:
                measurements[sample["sample_id"]] = {"error": str(exc), "predicates": groups,
                                                       "counts": [], "intersection": None, "measurement_complete": False}
        fixture_path = root / ".rag_data/techqa_fixture.sqlite"
        other_manifest = read_manifest(fixture_path) if fixture_path.is_file() else None
        zero_path = docs / "zero_predicate_registration.json"
        zero_data = json.loads(zero_path.read_text(encoding="utf-8")) if zero_path.is_file() else None
        zero_groups = {x["predicate_id"]: x["phrases"] for x in (zero_data or {}).get("predicates", [])}
        checks = []
        for row in rows:
            source_request = json.loads(row["input_source_and_selection"])
            measured = measurements[row["input_sample_id"]]
            if source_request.get("analysis_predicates"):
                groups = source_request["analysis_predicates"]
                measured = measure(db, groups) if all(group in zero_groups.values() for group in groups) else {
                    "error": "unregistered_zero_predicate", "counts": [], "measurement_complete": False}
            db_status = re.search(r"DB=([a-z_]+)", row["expected_worker_states"])[1]
            mock = row["planned_evidence_type"] == "契约测试(Mock)"
            has_data_assertion = db_status in {"completed", "no_data", "partial"}
            expects_zero = db_status == "no_data"
            consistency = "一致"
            reason = "真实语料前提可构造；在线状态/故障/预算契约仍未执行"
            if has_data_assertion and not measured.get("measurement_complete") and not mock:
                consistency, reason = "冲突", measured.get("error", "measurement_incomplete")
            elif expects_zero and measured.get("counts") and any(measured["counts"]):
                consistency, reason = "冲突", "完整计数非零；Mock零值不能替代真实语料前提"
            elif db_status == "completed" and measured.get("measurement_complete") and not any(measured["counts"]):
                consistency, reason = "冲突", "DB=completed的正常计数前提为真实零匹配，应为no_data；不得改状态门禁"
            if "data_version_mismatch" in row["assertions"]:
                if other_manifest is None or other_manifest.get("scope") == manifest["scope"]:
                    consistency, reason = "冲突", "缺少可构造版本/范围不匹配的真实数据输入；禁止固定数Mock顶替"
                else:
                    reason = "已有真实fixture索引scope与full不匹配；仅隔离配置指向它即可触发前置校验，源库不修改"
            null_assertions = re.findall(r"[^；。\n]*\bnull\b[^；。\n]*", row["assertions"])
            checks.append({"scenario_id": row["scenario_id"], "phase": row["phase"],
                           "spec_expected": {"worker_states": row["expected_worker_states"],
                                             "overall_status": row["expected_overall_status"],
                                             "assertions": row["assertions"],
                                             "full_count": 0 if expects_zero else "精确全集计数" if has_data_assertion else "不发布计数",
                                             "null_assertions": null_assertions},
                           "recomputed": measured, "consistency": consistency, "reason": reason,
                           "expected_evidence_type": row["planned_evidence_type"],
                           "evidence_type": "真实运行" if measured.get("measurement_complete") else "未执行",
                           "evidence_scope": "independent_read_only_full_corpus_recount;not_online_worker_or_gate",
                           "runtime_state_verified": False, "execution_status": "未执行",
                           "data_version_mismatch_input": other_manifest if "data_version_mismatch" in row["assertions"] else None})
    spec_items = inventory_spec(docs)
    report = {"schema_version": 2, "version": version, "generated_at": datetime.now(timezone.utc).isoformat(),
              "gate_scope": "specification_data_preflight", "system_gate_executed": False,
              "manifest": manifest, "actual_distinct_nonempty_documents": actual_total,
              "manifest_count_consistent": str(actual_total) == manifest.get("document_count"),
              "data_prerequisites_consistent": prereq_ok, "scenario_inventory": [x["scenario_id"] for x in rows],
              "scenario_checks": checks, "sample_measurements": measurements,
              "spec_assertion_inventory": spec_items, "inventory_complete": True,
              "conflicts": [x["scenario_id"] for x in checks if x["consistency"] == "冲突"],
              "consistency_counts": dict(Counter(x["consistency"] for x in checks)),
              "spec_source_sha256": {p.name: sha256(p) for p in docs.iterdir() if p.is_file()},
              "worker_calls": 0, "llm_calls": 0, "heldout_stage_calls_project2": 0,
              "heldout_repetitions_project2": 0,
              "limitations": ["语义适用性/真实RAG无答案需正常依赖实际运行，词项计数不能证明",
                              "预算/授权/null错误语义只核对数据前提；没有在线执行证据，不计系统门禁通过",
                              "不导入Worker/目录构建代码；不读取QA/目标/答案/Y-N/held-out"]}
    report["status"] = "passed" if not report["conflicts"] and prereq_ok and report["manifest_count_consistent"] else "failed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--version", default="v0.1", choices=("v0.1", "v0.2"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--register-zero", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.register_zero:
        registration = choose_zero_predicates(root / ".rag_data/techqa_full.sqlite", seed=20261005, quantity=2)
        args.register_zero.parent.mkdir(parents=True, exist_ok=True)
        args.register_zero.write_text(json.dumps(registration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.stdout.write(f"REGISTERED zero predicates SHA256={sha256(args.register_zero)}\n")
        return 0
    report = audit_specs(root, args.version)
    output = args.output or root / "audit/project2-v1/preflight_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"{report['status'].upper()} version={args.version} scenarios={len(report['scenario_checks'])} "
                     f"spec_lines={len(report['spec_assertion_inventory'])} samples={len(report['sample_measurements'])} "
                     f"conflicts={','.join(report['conflicts']) or 'none'}\n")
    for item in report["scenario_checks"]:
        sys.stdout.write(f"{item['scenario_id']} {item['consistency']} counts={item['recomputed'].get('counts')} "
                         f"intersection={item['recomputed'].get('intersection')} — {item['reason']}\n")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
