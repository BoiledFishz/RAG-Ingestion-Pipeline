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
