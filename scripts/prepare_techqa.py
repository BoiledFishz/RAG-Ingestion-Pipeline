"""Create traceable local fixtures and PDF/Markdown/OCR inputs from official TechQA text."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import fitz

from rag.techqa.data import (
    ARCHIVE_SHA256,
    DATA_ROOT,
    FIXTURE_ROOT,
    ROOT,
    digest,
    documents,
    question_text,
    questions,
)

LOGGER = logging.getLogger(__name__)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    train = questions("train")
    selected = [r for r in train if r["ANSWERABLE"] == "Y"][:12]
    selected += [r for r in train if r["ANSWERABLE"] == "N"][:3]
    wanted = {str(r["DOCUMENT"]) for r in selected if r["ANSWERABLE"] == "Y"}
    # Include official distractors; no invented negative documents.
    wanted.update(str(doc) for r in selected for doc in r["DOC_IDS"][:2])
    docs = [d for d in documents("core") if d["id"] in wanted]
    lookup = {doc["id"]: doc for doc in docs}
    missing = wanted - lookup.keys()
    if missing:
        raise ValueError(f"Missing official documents: {missing}")
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(FIXTURE_ROOT / "documents.json", docs)
    write_json(FIXTURE_ROOT / "questions.json", selected)
    shutil.copyfile(
        DATA_ROOT / "CDLA-Permissive-v1.0.pdf", FIXTURE_ROOT / "CDLA-Permissive-v1.0.pdf"
    )
    corpus = FIXTURE_ROOT / "mixed"
    corpus.mkdir(exist_ok=True)
    manifest = {}
    golden = []
    for number, row in enumerate(selected[:12]):
        doc = lookup[row["DOCUMENT"]]
        content = doc["title"] + "\n\n" + doc["text"]
        name = doc["id"] + ".md"
        (corpus / name).write_text(content, encoding="utf-8")
        manifest[name] = {
            "techqa_document_id": doc["id"],
            "dataset": "IBM TechQA",
            "original_text_sha256": digest(doc["text"]),
            "transformation": "title and official plain text, no paraphrasing",
        }
        evidence = str(row["ANSWER"]).strip()
        # Smallest complete official answer line, never a fabricated answer.
        lines = [v.strip() for v in evidence.splitlines() if len(v.strip()) >= 25]
        excerpt = min(lines, key=len) if lines else evidence
        golden.append(
            {
                "id": row["QUESTION_ID"],
                "question": question_text(row),
                "ground_truth": evidence,
                "reference_evidence": excerpt,
                "source_file": name,
                "techqa_document_id": doc["id"],
            }
        )
        if number == 0:
            # Same unmodified TechNote rendered as a text PDF and as a scan for OCR testing.
            pdf = fitz.open()
            blocks = content.splitlines(keepends=True)
            while blocks:
                page = pdf.new_page()
                cursor = 45
                while blocks and cursor < 780:
                    line = blocks.pop(0).rstrip()
                    import textwrap

                    wrapped = textwrap.wrap(line, width=88) or [""]
                    if cursor + 12 * len(wrapped) > 790:
                        blocks.insert(0, line)
                        break
                    page.insert_text((40, cursor), "\n".join(wrapped), fontsize=10)
                    cursor += 12 * len(wrapped)
            pdf.save(corpus / f"{doc['id']}.pdf")
            scan = fitz.open()
            for page in pdf:
                raster = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                scan.new_page(width=page.rect.width, height=page.rect.height).insert_image(
                    page.rect, stream=raster.tobytes("png")
                )
            scan.save(corpus / f"{doc['id']}-scan.pdf")
            scan.close()
            pdf.close()
            for suffix in [".pdf", "-scan.pdf"]:
                manifest[doc["id"] + suffix] = {
                    **manifest[name],
                    "transformation": "rendered official text; PDF/scan format test",
                }
    write_json(corpus / ".techqa-manifest.json", manifest)
    write_json(ROOT / "evals/golden_dataset.json", golden[:5])
    retrieval = []
    for number, row in enumerate(selected):
        answerable = row["ANSWERABLE"] == "Y"
        item = {
            "id": row["QUESTION_ID"],
            "question": question_text(row),
            "answerable": answerable,
            "category": "unanswerable"
            if not answerable
            else ("semantic" if number < 5 else "identifier" if number < 9 else "metadata"),
            "expected_sources": (
                [
                    row["DOCUMENT"] + ext
                    for ext in ([".md", ".pdf", "-scan.pdf"] if number == 0 else [".md"])
                ]
                if answerable
                else []
            ),
            "reference_evidence": [golden[number]["reference_evidence"]] if answerable else [],
            "filters": {"language": "en"} if 9 <= number < 12 else {},
            "official_question_id": row["QUESTION_ID"],
            "official_split": "train",
        }
        retrieval.append(item)
    write_json(ROOT / "evals/retrieval_golden_dataset.json", retrieval)
    manifest = {
        "dataset": "IBM TechQA",
        "upstream": "https://github.com/ibm/techqa",
        "archive_sha256": ARCHIVE_SHA256,
        "question_split": "train",
        "selection": "first 12 answerable + first 3 unanswerable training questions; "
        "answer documents and first two official DOC_IDS as distractors",
        "documents": len(docs),
        "questions": len(selected),
        "full_corpus": False,
        "content_hashes": {d["id"]: digest(d["text"]) for d in docs},
    }
    write_json(FIXTURE_ROOT / "manifest.json", manifest)
    LOGGER.info(
        "Prepared %d official documents and %d official questions", len(docs), len(selected)
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
