<#
.SYNOPSIS
  Chap12 real-model evaluation (Ollama qwen2.5:7b + nomic rerank) on this Windows machine.

.DESCRIPTION
  Run from the enterprise-ai-agent directory of a checkout (or worktree) of
  feature/chap12-supervisor-lite. Every output is JSON under evaluation/results/chap12/ or
  evaluation/chap12/tune/.
    0. Locates Python (.venv312 of this checkout, else of the main checkout) and the indices
       (.rag_data of this checkout, else a directory junction to the main checkout's .rag_data).
    1. Checks Ollama, pulls the two pinned models if missing, records versions and digests.
    2. Tune split only (each step skipped if its output already exists):
       a. nomic acceptance threshold      -> tune/thresholds.json (key nomic_rerank)
       b. refusal-signal study for nomic  -> tune/refusal_signals_nomic.json (adopt iff BA > 0.6)
       c. model product-pick order        -> tune/product_pick.json (first iff +0.05 over fallback)
       After step 2 the configuration is frozen: git status must show no change outside
       evaluation/ results; commit the tune outputs before step 3 (the script checks this).
    3. Evaluation split (sample): p1_single / single / multi, -Repeats times on the mixed task
       set; -LimitPerType N keeps the first N tasks of each type (seeded random order). 0 = all.
    4. -Confirm: the confirm2 split once (1 repeat), refused if any confirm2 run exists.
  Re-running with the same -RunName resumes an interrupted run.

.EXAMPLE
  ./evaluation/chap12_compare_real.ps1 -RunName ollama_run1 -LimitPerType 30 -Confirm
#>
param(
  [string]$RunName = "ollama_$(Get-Date -Format yyyyMMdd_HHmm)",
  [string]$Python = "",
  [string]$OllamaUrl = "http://localhost:11434",
  [int]$Repeats = 3,
  [int]$LimitPerType = 30,
  [switch]$Confirm,
  [switch]$TuneOnly
)
$ErrorActionPreference = "Stop"
$Model = "qwen2.5:7b"
$Embed = "nomic-embed-text"

# --- 0. locate Python and indices --------------------------------------------------------
$checkout = (Resolve-Path "..").Path
$common = (& git -c safe.directory=* rev-parse --path-format=absolute --git-common-dir).Trim()
$mainCheckout = Split-Path $common -Parent
if (-not $Python) {
  foreach ($root in @($checkout, $mainCheckout)) {
    $candidate = Join-Path $root ".venv312/Scripts/python.exe"
    if (Test-Path $candidate) { $Python = $candidate; break }
  }
  if (-not $Python) { throw "No .venv312 found in $checkout or $mainCheckout; pass -Python" }
}
$ragData = Join-Path $checkout ".rag_data"
if (-not (Test-Path (Join-Path $ragData "chap12_sample.sqlite"))) {
  $mainData = Join-Path $mainCheckout ".rag_data"
  if (-not (Test-Path (Join-Path $mainData "chap12_sample.sqlite"))) {
    throw "chap12 indices not found; rebuild with: python -m evaluation.chap12_rebuild_indices --rebuild --install"
  }
  if ((Test-Path $ragData) -and -not (Get-ChildItem -Force $ragData)) { Remove-Item $ragData }
  if (Test-Path $ragData) { throw "$ragData exists but has no chap12 indices" }
  New-Item -ItemType Junction -Path $ragData -Target $mainData | Out-Null
  Write-Host "Linked $ragData -> $mainData (junction)"
}
& $Python -m evaluation.chap12_rebuild_indices --check --splits sample,tune,confirm2
if ($LASTEXITCODE) { throw "index content differs from evaluation/chap12/index_digests.json" }

# --- 1. Ollama and metadata --------------------------------------------------------------
function Get-Digest([string]$name) {
  $tags = Invoke-RestMethod "$OllamaUrl/api/tags"
  $hit = $tags.models | Where-Object { $_.name -eq $name -or $_.name -eq "$name`:latest" }
  if ($hit) { return $hit[0].digest } else { return $null }
}
$version = (Invoke-RestMethod "$OllamaUrl/api/version").version   # fails fast if Ollama is down
foreach ($m in @($Model, $Embed)) {
  if (-not (Get-Digest $m)) { & ollama pull $m; if ($LASTEXITCODE) { throw "pull $m failed" } }
}

$env:PYTHONPATH = "../src;."
$env:PYTHONUTF8 = "1"
$env:AGENT_PROFILE = "ollama"
$env:AGENT_MODEL = $Model
$env:AGENT_OLLAMA_URL = $OllamaUrl
$env:OLLAMA_BASE_URL = $OllamaUrl
$env:TECHQA_RERANKER = "nomic"
$env:CHAP12_RERANKER = "nomic"

# --- 2. tune-split decisions -------------------------------------------------------------
$tune = "evaluation/chap12/tune"
$thresholds = Get-Content "$tune/thresholds.json" -Raw | ConvertFrom-Json
if (-not $thresholds.nomic_rerank) {
  & $Python -m evaluation.chap12_retrieval_tune --split tune --rerank nomic
  if ($LASTEXITCODE) { throw "nomic calibration failed" }
}
if (-not (Test-Path "$tune/refusal_signals_nomic.json")) {
  & $Python -m evaluation.chap12_refusal_signals --rerank nomic
  if ($LASTEXITCODE) { throw "nomic refusal-signal study failed" }
}
if (-not (Test-Path "$tune/product_pick.json")) {
  & $Python -m evaluation.chap12_product_study --pick
  if ($LASTEXITCODE) { throw "product-pick study failed" }
}
if ($TuneOnly) { Write-Host "Tune decisions written under $tune; commit them, then re-run."; exit 0 }
$dirty = & git -c safe.directory=* status --porcelain -- . ":(exclude)evaluation/results"
if ($dirty) { throw "Uncommitted changes (commit the tune outputs first):`n$($dirty -join "`n")" }

# --- 3. evaluation split -----------------------------------------------------------------
$out = "evaluation/results/chap12/$RunName"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$meta = [ordered]@{
  started_at      = (Get-Date).ToString("o")
  host            = $env:COMPUTERNAME
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
                                CHAP12_RERANKER = "nomic"; TECHQA_RERANKER = "nomic";
                                CHAP12_CRITIC = $env:CHAP12_CRITIC;
                                CHAP12_PRODUCT_PICK = $env:CHAP12_PRODUCT_PICK;
                                CHAP12_GAP_GATE = $env:CHAP12_GAP_GATE }
}
if (-not (Test-Path "$out/meta.json")) {
  $meta | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 "$out/meta.json"
}
& $Python -m evaluation.chap12_eval --split sample --repeats $Repeats `
    --limit-per-type $LimitPerType --output $out --meta "$out/meta.json" --resume
if ($LASTEXITCODE) { throw "evaluation failed (re-run the same command to resume)" }

# --- 4. confirmation split (once) --------------------------------------------------------
if ($Confirm) {
  $c = "evaluation/results/chap12/${RunName}_confirm2_once"
  $other = Get-ChildItem "evaluation/results/chap12" -Directory -Filter "*confirm2_once" |
    Where-Object { $_.FullName -ne (Resolve-Path -LiteralPath $c -ErrorAction SilentlyContinue).Path }
  if ($other) { throw "confirm2 already used by: $($other.Name -join ', ')" }
  if ((Test-Path "$c/summary.json")) { throw "confirm2 split already run once: $c" }
  & $Python -m evaluation.chap12_eval --split confirm2 --repeats 1 `
      --limit-per-type $LimitPerType --output $c --meta "$out/meta.json" --resume
  if ($LASTEXITCODE) { throw "confirm run failed (re-run to resume)" }
}
Write-Host "Done: $out/summary.json"
