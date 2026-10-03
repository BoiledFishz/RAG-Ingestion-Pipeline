param([string]$ResultPrefix = ('techqa_agents_' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference = 'Stop'
if ($ResultPrefix -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple result directory name.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $projectRoot '.venv312\Scripts\python.exe'
}
$env:TECHQA_PROFILE = 'full'
$env:TECHQA_DENSE_BACKEND = 'semantic'
$env:TECHQA_RERANKER = 'nomic'
$env:AGENT_PROFILE = 'ollama'
$env:AGENT_RETRIEVAL_BACKEND = 'techqa'
$env:MODEL_PROVIDER = 'ollama'
$env:RAG_BACKEND = 'techqa'
$workflowFailed = $false
Push-Location -LiteralPath (Join-Path $projectRoot 'agentic-rag-homework')
try {
    & $pythonPath -m evaluation.run --provider ollama --planner-runs 10 --output "evaluation/results/$ResultPrefix"
    if ($LASTEXITCODE -ne 0) {
        $workflowFailed = $true
        Write-Warning 'Agent comparison failed; preserving failures and continuing other checks.'
    }
    & $pythonPath -m evaluation.critic_stability --limit 5 --repeats 2 --output "evaluation/results/${ResultPrefix}_critic"
    if ($LASTEXITCODE -ne 0) {
        $workflowFailed = $true
        Write-Warning 'Critic reference check failed; continuing other checks.'
    }
    & $pythonPath -m evaluation.critic_stability --evidence-mode retrieved --split fixture --label all --limit 15 --repeats 2 --output "evaluation/results/${ResultPrefix}_critic_retrieved"
    if ($LASTEXITCODE -ne 0) {
        $workflowFailed = $true
        Write-Warning 'Critic with actual retrieval failed; continuing HTTP and regression checks.'
    }
} finally { Pop-Location }
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath scripts/smoke_techqa.py --output "evals/${ResultPrefix}_api_smoke.json"
    if ($LASTEXITCODE -ne 0) { $workflowFailed = $true }
    & $pythonPath scripts/test_all.py
    if ($LASTEXITCODE -ne 0) { $workflowFailed = $true }
} finally { Pop-Location }
if ($workflowFailed) {
    throw 'Agent workflow checks failed; inspect recorded cases. Independent checks completed.'
}
Write-Host 'Agent workflow checks completed. Review answer metrics before production sign-off.'
