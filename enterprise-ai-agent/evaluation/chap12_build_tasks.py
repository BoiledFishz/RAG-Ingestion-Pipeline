"""P1-1: fixed mixed task set (explain / data / explain_and_data) with independent gold.

    python -m evaluation.chap12_build_tasks --split sample --seed 20261021
    python -m evaluation.chap12_build_tasks --split confirm --seed 20261023

* explain and explain_and_data: the split's sampled questions, shuffled with the seed inside
  each Y/N stratum and dealt alternately to the two types (so both keep the Y/N mix).
* data: 60 questions generated from three templates over products of the split's own index
  (20 each). Gold values are recomputed here from the raw official metadata JSON in `docs`,
  with an independent re-implementation of the doc-class rule: no Worker code is used.
Outputs <folder>/mixed_tasks.jsonl (no answers) and <folder>/mixed_gold.jsonl (scoring only).
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

HERE = Path(__file__).resolve().parent / "chap12"
CLASS_LABEL = {"apar": "APAR (fix)", "technote": "technote",
               "product_documentation": "product documentation"}


def doc_class(doc_id: str) -> str:
    # Independent re-implementation of the documented prefix rule (spec §5).
    if doc_id[:4] == "swg1":
        return "apar"
    if doc_id[:5] == "swg27":
        return "product_documentation"
    return "technote" if doc_id[:4] == "swg2" else "other"


def raw_documents(index: Path) -> list[dict[str, Any]]:
    db = sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)
    rows = db.execute("SELECT doc_id, metadata FROM docs ORDER BY doc_id").fetchall()
    out = []
    for doc, raw in rows:
        meta = json.loads(raw)
        date = str(meta.get("date") or "")
        out.append({"doc_id": doc, "ids": {p.strip() for p in str(meta.get("productId") or "")
                                           .split(",") if p.strip()},
                    "name": str(meta.get("productName") or "").strip(),
                    "date": date if len(date) == 10 and date[4] == "-" else None,
                    "class": doc_class(doc)})
    return out


def build_data_tasks(docs: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    names: dict[str, Counter[str]] = defaultdict(Counter)
    members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in docs:
        for pid in d["ids"]:
            members[pid].append(d)
        if len(d["ids"]) == 1 and d["name"]:
            names[next(iter(d["ids"]))][d["name"]] += 1
    products = sorted(p for p in names if len(members[p]) >= 5)
    rng.shuffle(products)
    tasks: list[dict[str, Any]] = []
    for i, pid in enumerate(products[:60]):
        name = names[pid].most_common(1)[0][0]
        pool = members[pid]
        template = ("count_since", "list_recent_apar", "count_by_year")[i % 3]
        request: dict[str, Any]
        gold: dict[str, Any]
        if template == "count_since":
            years = sorted({d["date"][:4] for d in pool if d["date"]})
            year = rng.choice(years) if years else "2010"
            klass = rng.choice(["technote", "apar"])
            query = (f"How many {CLASS_LABEL[klass]} documents about {name} have been "
                     f"published since {year}?")
            request = {"operation": "count_documents", "product": pid,
                       "date_from": f"{year}-01-01", "doc_class": klass}
            gold = {"count": sum(1 for d in pool if d["class"] == klass and d["date"]
                                 and d["date"] >= f"{year}-01-01")}
        elif template == "list_recent_apar":
            query = f"List the most recent APAR (fix) documents for {name}."
            request = {"operation": "list_recent_documents", "product": pid,
                       "doc_class": "apar", "limit": 5}
            chosen = sorted((d for d in pool if d["class"] == "apar"), key=lambda d: d["doc_id"])
            chosen.sort(key=lambda d: d["date"] or "", reverse=True)
            gold = {"rows": [d["doc_id"] for d in chosen[:5]]}
        else:
            query = f"How many {name} documents are there per year?"
            request = {"operation": "count_by_year", "product": pid}
            per_year = Counter(d["date"][:4] for d in pool if d["date"])
            gold = {"by_year": dict(sorted(per_year.items()))}
        tasks.append({"type": "data", "template": template, "query": query,
                      "goal": "data", "data_request": request, "gold": gold})
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split",
                        choices=["sample", "confirm", "confirm2", "tune"], required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    folder = HERE if args.split == "sample" else HERE / args.split
    index = ROOT / f".rag_data/chap12_{args.split}.sqlite"
    rng = random.Random(args.seed)
    questions = [json.loads(x) for x in (folder / "tasks.jsonl").read_text("utf-8").splitlines()]
    gold = {g["task_id"]: g for g in map(json.loads,
                                         (folder / "gold.jsonl").read_text("utf-8").splitlines())}
    typed: list[dict[str, Any]] = []
    for label in ("Y", "N"):
        stratum = [q for q in questions if gold[q["task_id"]]["answerable"] == label]
        rng.shuffle(stratum)
        for k, q in enumerate(stratum):
            kind = ("explain", "explain_and_data")[k % 2]
            typed.append({"type": kind, "source_task_id": q["task_id"],
                          "question_id": q["question_id"], "query": q["query"], "goal": kind})
    typed += build_data_tasks(raw_documents(index), rng)
    order = {"explain": 0, "explain_and_data": 1, "data": 2}
    rng.shuffle(typed)  # random order inside each type => any prefix is a random subset
    typed.sort(key=lambda t: order[t["type"]])
    tasks_out = folder / "mixed_tasks.jsonl"
    gold_out = folder / "mixed_gold.jsonl"
    for path in (tasks_out, gold_out):
        if path.exists():
            raise FileExistsError(f"{path} exists; task sets are immutable")
    with tasks_out.open("x", encoding="utf-8") as t, gold_out.open("x", encoding="utf-8") as g:
        for n, task in enumerate(typed, 1):
            task_id = f"M-{args.split}-{n:03d}"
            public = {"task_id": task_id, "type": task["type"], "query": task["query"],
                      "goal": task["goal"]}
            if "data_request" in task:
                public["data_request"] = task["data_request"]
            t.write(json.dumps(public, ensure_ascii=False) + "\n")
            row: dict[str, Any] = {"task_id": task_id, "type": task["type"]}
            if task["type"] == "data":
                row |= {"template": task["template"], **task["gold"]}
            else:
                q = gold[task["source_task_id"]]
                row |= {"source_task_id": task["source_task_id"], "answerable": q["answerable"],
                        "document": q["document"], "answer": q["answer"]}
            g.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"split": args.split, "seed": args.seed,
                      "counts": dict(Counter(t["type"] for t in typed))}, indent=1))


if __name__ == "__main__":
    main()
