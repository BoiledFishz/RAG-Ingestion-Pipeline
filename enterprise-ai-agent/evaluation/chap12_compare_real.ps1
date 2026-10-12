<#
.SYNOPSIS
  Chap12 real-model evaluation (Ollama qwen2.5:7b + nomic rerank) on this Windows machine.

.DESCRIPTION
  Run from the enterprise-ai-agent directory of a checkout of feature/chap12-supervisor-lite.
  Nothing is graded by a human; every output is JSON under evaluation/results/chap12/.
    1. Checks Ollama, pulls the two pinned models if missing, records versions and digests.
    2. Tune split only: calibrates the nomic acceptance threshold and the refusal-signal study
       (skipped if already present in evaluation/chap12/tune/; delete the keys to redo).
    3. Evaluation split: p1_single / single / multi, -Repeats times (default 3), on the mixed
       task set; -LimitPerType N keeps the first N tasks of each type (file order is random
       within a type, so this is a seeded stratified subset). 0 = all 210 tasks.
    4. Optional -Confirm: the confirm split once (1 repeat). Run it only once, ever.
  Re-running with the same -RunName resumes an interrupted run.

.EXAMPLE
  ./evaluation/chap12_compare_real.ps1 -RunName ollama_run1 -LimitPerType 30
#>
param(
  [string]$RunName = "ollama_$(Get-Date -Format yyyyMMdd_HHmm)",
  [string]$Python = "../.venv312/Scripts/python.exe",
  [string]$OllamaUrl = "http://localhost:11434",
  [int]$Repeats = 3,
  [int]$LimitPerType = 30,
  [switch]$Confirm
)
$ErrorActionPreference = "Stop"
$Model = "qwen2.5:7b"
$Embed = "nomic-embed-text"

function Get-Digest([string]$name) {
  $tags = Invoke-RestMethod "$OllamaUrl/api/tags"
  $hit = $tags.models | Where-Object { $_.name -eq $name -or $_.name -eq "$name`:latest" }
  if ($hit) { return $hit[0].digest } else { return $null }
}

$version = (Invoke-RestMethod "$OllamaUrl/api/version").version   # fails fast if Ollama is down
foreach ($m in @($Model, $Embed)) {
  if (-not (Get-Digest $m)) { & ollama pull $m; if ($LASTEXITCODE) { throw "pull $m failed" } }
}
$out = "evaluation/results/chap12/$RunName"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$meta = [ordered]@{
  started_at      = (Get-Date).ToString("o")
  ollama_url      = $OllamaUrl
  ollama_version  = $version
  model           = $Model
  model_digest    = Get-Digest $Model
  embed_model     = $Embed
  embed_digest    = Get-Digest $Embed
  python          = (& $Python --version)
  git_commit      = (& git -c safe.directory=* rev-parse HEAD)
  repeats         = $Repeats
  limit_per_type  = $LimitPerType
  env             = [ordered]@{ AGENT_PROFILE = "ollama"; AGENT_MODEL = $Model;
                                CHAP12_RERANKER = "nomic"; TECHQA_RERANKER = "nomic" }
}
$meta | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 "$out/meta.json"

$env:PYTHONPATH = "../src;."
$env:AGENT_PROFILE = "ollama"
$env:AGENT_MODEL = $Model
$env:AGENT_OLLAMA_URL = $OllamaUrl
$env:OLLAMA_BASE_URL = $OllamaUrl
$env:TECHQA_RERANKER = "nomic"
$env:CHAP12_RERANKER = "nomic"

$thresholds = Get-Content "evaluation/chap12/tune/thresholds.json" -Raw | ConvertFrom-Json
if (-not $thresholds.nomic_rerank) {
  & $Python -m evaluation.chap12_retrieval_tune --split tune --rerank nomic
  if ($LASTEXITCODE) { throw "nomic calibration failed" }
}
if (-not (Test-Path "evaluation/chap12/tune/refusal_signals_nomic.json")) {
  & $Python -m evaluation.chap12_refusal_signals --rerank nomic
  if ($LASTEXITCODE) { throw "nomic refusal-signal study failed" }
}

& $Python -m evaluation.chap12_eval --split sample --repeats $Repeats `
    --limit-per-type $LimitPerType --output $out --meta "$out/meta.json" --resume
if ($LASTEXITCODE) { throw "evaluation failed (re-run the same command to resume)" }

if ($Confirm) {
  $c = "evaluation/results/chap12/${RunName}_confirm_once"
  if ((Test-Path "$c/summary.json")) { throw "confirm split already run once: $c" }
  & $Python -m evaluation.chap12_eval --split confirm --repeats 1 `
      --limit-per-type $LimitPerType --output $c --meta "$out/meta.json" --resume
  if ($LASTEXITCODE) { throw "confirm run failed (re-run to resume)" }
}
Write-Host "Done: $out/summary.json"
