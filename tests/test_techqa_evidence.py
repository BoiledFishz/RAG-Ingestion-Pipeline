from rag.techqa.data import documents, question_text, questions
from rag.techqa.evidence import answer_passages


def test_official_solution_remains_verbatim_without_document_footer():
    question = questions("fixture")[0]
    doc = next(d for d in documents("fixture") if d["id"] == question["DOCUMENT"])
    passages = answer_passages(question_text(question), doc["text"], limit=2)
    assert passages and len(passages) <= 2
    assert "setproperty" in passages[0].text
    assert all(p.text in doc["text"] and len(p.text) <= 900 for p in passages)
    assert all("RELATED INFORMATION" not in p.text for p in passages)


def test_direct_scope_explanation_is_preferred_to_nested_function_example():
    question = next(q for q in questions("fixture") if q["DOCUMENT"] == "swg21675316")
    doc = next(d for d in documents("fixture") if d["id"] == question["DOCUMENT"])
    passage = answer_passages(question_text(question), doc["text"], limit=1)[0]
    assert "immediate scope" in passage.text
    assert "set a variable" in passage.text
    assert passage.text in doc["text"]


def test_vulnerability_question_preserves_affected_versions():
    question = next(q for q in questions("fixture") if "CVE-2017-3156" in question_text(q))
    doc = next(d for d in documents("fixture") if d["id"] == question["DOCUMENT"])
    passage = answer_passages(question_text(question), doc["text"], limit=1)[0]
    assert "AFFECTED PRODUCTS AND VERSIONS" in passage.text
    assert "4.1.1" in passage.text and "4.2.0" in passage.text
    assert passage.text in doc["text"]


def test_retrieved_deep_solution_is_preserved_after_parent_expansion():
    question = next(q for q in questions("fixture") if q["DOCUMENT"] == "swg21179559")
    doc = next(d for d in documents("fixture") if d["id"] == question["DOCUMENT"])
    position = doc["text"].index("SSLClientAuth")
    excerpt = doc["text"][max(0, position - 150):position + 400]
    passage = answer_passages(question_text(question), doc["text"], limit=1,
                              retrieved_excerpt=excerpt)[0]
    assert "SSLClientAuth" in passage.text
    assert passage.text in doc["text"]


def test_real_dangling_instruction_hint_keeps_all_rollback_steps():
    doc = next(d for d in documents("regression") if d["id"] == "swg21960632")
    query = question_text(questions("regression")[0])
    start = doc["text"].index("This issue will be resolved")
    end = doc["text"].index("do the following:") + len("do the following:")
    passage = answer_passages(query, doc["text"], limit=1,
                              retrieved_excerpt=doc["text"][start:end])[0]
    assert "1. Open consoleSetupEnv.sh" in passage.text
    assert "5. Save the updated consoleSetupEnv.sh." in passage.text
    assert not passage.text.rstrip().endswith(":")
    assert passage.text in doc["text"] and len(passage.text) <= 1800


def test_original_instruction_intro_without_steps_is_not_published():
    from rag.techqa.evidence import complete_instructions

    doc = next(d for d in documents("regression") if d["id"] == "swg21960632")
    end = doc["text"].index("do the following:") + len("do the following:")
    broken_input = doc["text"][:end]  # Truncated real data, never invented prose.
    assert complete_instructions("do the following:", broken_input) == ""
    assert complete_instructions("do the following:", doc["text"], max_chars=30) == ""


def test_real_multi_paragraph_list_preserves_final_step_and_original_text():
    from rag.techqa.evidence import complete_instructions

    doc = next(d for d in documents("regression") if d["id"] == "swg21679259")
    intro = "Please follow steps below to resolve this issue:"
    passage = complete_instructions(intro, doc["text"])
    assert "6. Test if logout works as desired." in passage
    assert "Following steps applies" not in passage  # A separate conditional procedure.
    assert passage in doc["text"]


def test_original_security_bulletin_footer_is_excluded_even_after_a_table():
    doc = next(d for d in documents("fixture")
               if "GET NOTIFIED ABOUT FUTURE SECURITY BULLETINS" in d["text"])
    passages = answer_passages(doc["title"], doc["text"])
    assert passages and all(p.text in doc["text"] for p in passages)
    assert all("GET NOTIFIED ABOUT FUTURE SECURITY BULLETINS" not in p.text for p in passages)


def test_actual_new_version_requirement_cannot_use_an_older_error_prerequisite():
    from rag.techqa.query import requirement_error_conflict

    query = question_text(next(q for q in questions("regression")
                              if q["QUESTION_ID"] == "DEV_Q000"))
    docs = {d["id"]: d for d in documents("regression")}
    assert requirement_error_conflict(query, docs["swg21681385"]["text"])
    assert not requirement_error_conflict(query, docs["swg24042191"]["text"])
    # Original older error matched against itself is still a valid premise.
    assert not requirement_error_conflict(docs["swg21681385"]["text"],
                                          docs["swg21681385"]["text"])
    assert not requirement_error_conflict(query, docs["swg21960632"]["text"])
