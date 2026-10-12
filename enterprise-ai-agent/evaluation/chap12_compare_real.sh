#!/usr/bin/env bash
# Linux/macOS equivalent of chap12_compare_real.ps1 (same steps and outputs).
# Usage: RUN_NAME=ollama_run1 LIMIT_PER_TYPE=30 REPEATS=3 ./evaluation/chap12_compare_real.sh [--confirm]
set -euo pipefail
RUN_NAME=${RUN_NAME:-ollama_$(date +%Y%m%d_%H%M)}
PYTHON=${PYTHON:-python}
OLLAMA_URL=${OLLAMA_URL:-http://localhost:11434}
REPEATS=${REPEATS:-3}
LIMIT_PER_TYPE=${LIMIT_PER_TYPE:-30}
MODEL=qwen2.5:7b
EMBED=nomic-embed-text
digest() { curl -fsS "$OLLAMA_URL/api/tags" | "$PYTHON" -c "import json,sys;m=[x['digest'] for x in json.load(sys.stdin)['models'] if x['name'] in ('$1','$1:latest')];print(m[0] if m else '')"; }
VERSION=$(curl -fsS "$OLLAMA_URL/api/version" | "$PYTHON" -c "import json,sys;print(json.load(sys.stdin)['version'])")
for m in "$MODEL" "$EMBED"; do [ -n "$(digest "$m")" ] || ollama pull "$m"; done
OUT=evaluation/results/chap12/$RUN_NAME
mkdir -p "$OUT"
"$PYTHON" - "$OUT/meta.json" <<PY
import json,sys,subprocess,datetime,platform
json.dump({"started_at": datetime.datetime.now().astimezone().isoformat(), "ollama_url": "$OLLAMA_URL",
 "ollama_version": "$VERSION", "model": "$MODEL", "model_digest": "$(digest "$MODEL")",
 "embed_model": "$EMBED", "embed_digest": "$(digest "$EMBED")", "python": platform.python_version(),
 "git_commit": subprocess.run(["git","-c","safe.directory=*","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip(),
 "repeats": $REPEATS, "limit_per_type": $LIMIT_PER_TYPE}, open(sys.argv[1],"w"), indent=1)
PY
export PYTHONPATH=../src:. AGENT_PROFILE=ollama AGENT_MODEL=$MODEL AGENT_OLLAMA_URL=$OLLAMA_URL \
  OLLAMA_BASE_URL=$OLLAMA_URL TECHQA_RERANKER=nomic CHAP12_RERANKER=nomic
grep -q nomic_rerank evaluation/chap12/tune/thresholds.json || \
  "$PYTHON" -m evaluation.chap12_retrieval_tune --split tune --rerank nomic
[ -f evaluation/chap12/tune/refusal_signals_nomic.json ] || \
  "$PYTHON" -m evaluation.chap12_refusal_signals --rerank nomic
"$PYTHON" -m evaluation.chap12_eval --split sample --repeats "$REPEATS" \
  --limit-per-type "$LIMIT_PER_TYPE" --output "$OUT" --meta "$OUT/meta.json" --resume
if [ "${1:-}" = "--confirm" ]; then
  C=evaluation/results/chap12/${RUN_NAME}_confirm_once
  [ ! -f "$C/summary.json" ] || { echo "confirm split already run once: $C"; exit 1; }
  "$PYTHON" -m evaluation.chap12_eval --split confirm --repeats 1 \
    --limit-per-type "$LIMIT_PER_TYPE" --output "$C" --meta "$OUT/meta.json" --resume
fi
echo "Done: $OUT/summary.json"
