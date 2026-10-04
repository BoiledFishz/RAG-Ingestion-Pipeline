from rag.techqa.data import documents, question_text, questions
from rag.techqa.evidence import aspect_passages


def original(case: str, scope: str) -> tuple[str, str]:
    question = next(q for q in questions(scope) if q["QUESTION_ID"] == case)
    doc = next(d for d in documents(scope) if d["id"] == question["DOCUMENT"])
    return question_text(question), doc["title"] + "\n\n" + doc["text"]


def test_version_comparison_keeps_both_package_rules_without_download_noise():
    query, parent = original("DEV_Q007", "regression")
    units = aspect_passages(query, parent)
    assert len(units) == 2
    assert "single package" in units[0].text
    assert "separate package" in units[1].text and "CN6H5EN" in units[1].text
    assert all("Passport Advantage website" not in u.text for u in units)
    assert all(parent[u.start_char:u.end_char] == u.text for u in units)


def test_bulletin_keeps_description_exposure_condition_and_remediation_together():
    query, parent = original("TRAIN_Q006", "fixture")
    text = "\n".join(p.text for p in aspect_passages(query, parent))
    assert "CVE-2017-3156" in text and "OAuth2 Hawk" in text
    assert "4.1.1" in text and "4.2.0" in text and "Huawei MTOSI Collector install" in text
    assert "IV99816" in text and "FixPack 3" in text
    assert "GET NOTIFIED" not in text


def test_credential_configuration_is_not_discarded_before_resolution_heading():
    query, parent = original("TRAIN_Q007", "fixture")
    text = "\n".join(p.text for p in aspect_passages(query, parent))
    assert "Default behaviour when no credentials" in text
    assert "component-managed authentication alias" in text
    assert "-componentAuthAlias myalias" in text and "Jython" in text


def test_release_specific_procedure_keeps_setup_and_correct_version_final_step():
    query, parent = original("TRAIN_Q011", "fixture")
    units = aspect_passages(query, parent)
    assert len(units) == 2
    text = "\n".join(p.text for p in units)
    assert "cd /Applications/IBM/SPSS/Statistics/" in text
    assert "sudo chown -R root:admin 25" in text
    assert "6. License your IBM SPSS Statistics product." in text
    assert "sudo chown -R root:admin 20" not in text
    assert all(parent[u.start_char:u.end_char] == u.text for u in units)
