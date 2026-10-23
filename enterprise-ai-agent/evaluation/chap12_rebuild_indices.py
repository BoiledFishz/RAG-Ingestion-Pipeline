"""Item 13: rebuild the Chap12 sample/tune/confirm/confirm2 indices and verify they are identical.

The indices (`.rag_data/chap12_{sample,tune,confirm,confirm2}.sqlite` and their
`.dense.sqlite` sidecars) are not committed (about 0.6 GB). Their logical content is pinned in
`evaluation/chap12/index_digests.json`: a SHA-256 over every row of every content table,
in a fixed order (file bytes are not compared: SQLite page layout may differ between builds).

    python -m evaluation.chap12_rebuild_indices --record           # pin digests of current files
    python -m evaluation.chap12_rebuild_indices --check            # digest current files only
    python -m evaluation.chap12_rebuild_indices --rebuild [--install] [--splits sample,tune]

--rebuild builds every split into a temporary folder with the original commands and seeds,
compares the index digests and the regenerated tasks/gold files with the committed ones, and
with --install copies verified indices into `.rag_data`. Needs the full TechQA index
(`.rag_data/techqa_full.sqlite`) and the semantic index (`.rag_data/techqa_semantic`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

AGENT = Path(__file__).resolve().parents[1]
HERE = AGENT / "evaluation/chap12"
DIGESTS = HERE / "index_digests.json"
# split -> (seed, committed folder, manifests whose questions are excluded)
SPLITS: dict[str, tuple[int, Path, list[Path]]] = {
    "sample": (20261011, HERE, []),
    "tune": (20261012, HERE / "tune", [HERE / "sample_manifest.json"]),
    "confirm": (20261013, HERE / "confirm",
                [HERE / "sample_manifest.json", HERE / "tune/sample_manifest.json"]),
    # Second confirmation split (2026-10-17): the configuration changed after the first one
    # was run, so the single real-model confirmation run uses this fresh split.
    "confirm2": (20261014, HERE / "confirm2",
                 [HERE / "sample_manifest.json", HERE / "tune/sample_manifest.json",
                  HERE / "confirm/sample_manifest.json"]),
}
CONTENT_TABLES = {"index": ["manifest", "docs", "technotes", "document_products", "vocabulary"],
                  "dense": ["manifest", "chunks"]}
COMPARED_FILES = ["tasks.jsonl", "gold.jsonl"]


def digest(path: Path, kind: str) -> dict[str, Any]:
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    out: dict[str, Any] = {}
    try:
        for table in CONTENT_TABLES[kind]:
            columns = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
            order = ", ".join(f'"{c}"' for c in columns)
            h = hashlib.sha256()
            rows = 0
            for row in db.execute(f'SELECT {order} FROM "{table}" ORDER BY {order}'):
                h.update(json.dumps([r.hex() if isinstance(r, bytes) else r for r in row],
                                    ensure_ascii=False).encode("utf-8"))
                rows += 1
            out[table] = {"rows": rows, "sha256": h.hexdigest()}
    finally:
        db.close()
    return out


def current(split: str) -> dict[str, Path]:
    base = ROOT / f".rag_data/chap12_{split}.sqlite"
    return {"index": base, "dense": base.with_suffix(".dense.sqlite")}


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run([sys.executable, "-m", *args], cwd=AGENT, check=True)


def rebuild(split: str, workdir: Path) -> dict[str, Path]:
    seed, _, excluded = SPLITS[split]
    out = workdir / split
    out.mkdir(parents=True, exist_ok=True)
    index = out / f"chap12_{split}.sqlite"
    run("evaluation.chap12_build_sample", "--seed", str(seed), "--index", str(index),
        "--output", str(out), *(["--exclude-manifest", *map(str, excluded)] if excluded else []))
    run("evaluation.chap12_build_dense", "--index", str(index))
    return {"index": index, "dense": index.with_suffix(".dense.sqlite"), "folder": out}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--rebuild", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--splits", default="sample,tune,confirm,confirm2")
    parser.add_argument("--workdir", type=Path, default=None)
    args = parser.parse_args()
    splits = [s for s in args.splits.split(",") if s]
    pinned = json.loads(DIGESTS.read_text("utf-8")) if DIGESTS.is_file() else {}

    if args.record:
        for split in splits:
            pinned[split] = {kind: digest(path, kind) for kind, path in current(split).items()}
        DIGESTS.write_text(json.dumps(pinned, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(pinned, indent=1))
        return

    ok = True
    report: dict[str, Any] = {}
    workdir = args.workdir or Path(tempfile.mkdtemp(prefix="chap12-rebuild-"))
    for split in splits:
        paths: dict[str, Path] = current(split) if args.check else rebuild(split, workdir)
        result: dict[str, Any] = {}
        for kind in ("index", "dense"):
            got = digest(paths[kind], kind)
            result[kind] = got == pinned.get(split, {}).get(kind)
        if args.rebuild:
            committed = SPLITS[split][1]
            for name in COMPARED_FILES:
                result[name] = (paths["folder"] / name).read_bytes() == \
                    (committed / name).read_bytes()
        report[split] = result
        ok = ok and all(result.values())
        if args.rebuild and args.install and all(result.values()):
            for kind in ("index", "dense"):
                shutil.copyfile(paths[kind], current(split)[kind])
            result["installed"] = True
    print(json.dumps({"workdir": str(workdir), "identical": ok, "splits": report}, indent=1))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
