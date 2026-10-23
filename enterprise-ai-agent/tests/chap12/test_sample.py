from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agents.chap12.sample import candidate_doc_ids, doc_class, select_questions, write_index

QUESTIONS = [{"QUESTION_ID": f"TRAIN_Q{i:03d}", "DOC_IDS": [f"d{i}", f"d{i + 1}"]}
             for i in range(300)]


def test_selection_is_seeded_bounded_and_order_independent() -> None:
    first = select_questions(QUESTIONS, 150, 7)
    again = select_questions(list(reversed(QUESTIONS)), 150, 7)
    assert first == again and len(first) == 150
    assert select_questions(QUESTIONS, 150, 8) != first
    for bad in (99, 201):
        with pytest.raises(ValueError):
            select_questions(QUESTIONS, bad, 7)


def test_corpus_is_union_of_official_candidates() -> None:
    assert candidate_doc_ids(QUESTIONS[:2]) == ["d0", "d1", "d2"]


def test_doc_class_from_official_id_prefix() -> None:
    assert [doc_class(x) for x in ("swg1PK69015", "swg27038498", "swg21996508", "nas8N1")] \
        == ["apar", "product_documentation", "technote", "other"]


def test_index_holds_no_qa_fields_and_is_immutable(sample_index: Path) -> None:
    db = sqlite3.connect(sample_index.as_uri() + "?mode=ro", uri=True)
    columns = {c[1] for t in ("docs", "technotes", "document_products")
               for c in db.execute(f"PRAGMA table_info({t})")}
    assert not columns & {"ANSWER", "answer", "ANSWERABLE", "QUESTION_ID", "DOCUMENT"}
    with pytest.raises(FileExistsError):
        write_index(sample_index, [], {})
