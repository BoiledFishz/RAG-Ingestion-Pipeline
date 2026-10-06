"""Preflight contracts: real corpus, exhaustive inventory, no online/oracle inputs."""

from pathlib import Path

from scripts.spec_preflight import audit_specs, choose_zero_predicates, read_manifest


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / ".rag_data/techqa_full.sqlite"


def test_every_scenario_and_numeric_spec_line_is_inventoried() -> None:
    report = audit_specs(ROOT, "v0.1")
    assert len(report["scenario_inventory"]) == 42
    assert set(report["scenario_inventory"]) == {x["scenario_id"] for x in report["scenario_checks"]}
    assert report["spec_assertion_inventory"]
    assert all(x["source_line"] and x["source_text"] for x in report["spec_assertion_inventory"])
    assert report["inventory_complete"] is True
    assert report["worker_calls"] == report["llm_calls"] == report["heldout_stage_calls_project2"] == 0
    assert len(report["sample_measurements"]) == 50


def test_conflicting_first_case_does_not_stop_later_checks() -> None:
    report = audit_specs(ROOT, "v0.1")
    checks = {x["scenario_id"]: x for x in report["scenario_checks"]}
    assert checks["AC12-02"]["consistency"] == "冲突"
    assert checks["AC12-02"]["recomputed"]["counts"] == [192]
    assert checks["AC12-11"]["recomputed"]["intersection"] is not None
    assert checks["AC12-23"]["recomputed"]["counts"][0] > 0
    assert checks["AC16-04"]["execution_status"] == "未执行"


def test_zero_predicates_are_repeatable_and_really_zero() -> None:
    first = choose_zero_predicates(DATABASE, seed=20261005, quantity=2)
    second = choose_zero_predicates(DATABASE, seed=20261005, quantity=2)
    assert first == second
    assert set(first["input_dependencies"]) <= {"official_full_corpus_titles", "official_full_corpus_fts", "approved_literal_patterns"}
    assert len(first["predicates"]) == 2
    assert all(x["count"] == 0 and x["measurement_complete"] for x in first["predicates"])
    assert all(all(n > 0 for n in x["individual_phrase_counts"]) for x in first["predicates"])
    assert all(x["phrase_roles"] == ["product_or_component", "version"] for x in first["predicates"])


def test_version_mismatch_can_use_an_existing_real_index() -> None:
    full = read_manifest(DATABASE)
    other = read_manifest(ROOT / ".rag_data/techqa_fixture.sqlite")
    assert full["scope"] == "full"
    assert other["scope"] != full["scope"]
