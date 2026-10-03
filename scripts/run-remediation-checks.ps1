param([string]$ResultPrefix = ('techqa_remediation_' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference = 'Stop'
if ($ResultPrefix -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple result directory name.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install the project virtual environment first.' }
function Invoke-PythonCheck {
    param([string[]]$PythonArgs, [string]$LogPath)
    $savedPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5 can treat ordinary native stderr logging as an
        # ErrorRecord when redirected. Exit codes determine stage success.
        $ErrorActionPreference = 'Continue'
        & $pythonPath @PythonArgs *> $LogPath
        return $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
}
$enterpriseResult = Join-Path $projectRoot "enterprise-ai-agent/evaluation/results/$ResultPrefix"
$agentResult = Join-Path $projectRoot "agentic-rag-homework/evaluation/results/$ResultPrefix"
$criticResult = Join-Path $projectRoot "agentic-rag-homework/evaluation/results/${ResultPrefix}_critic"
$apiResult = Join-Path $projectRoot "evals/${ResultPrefix}_api_smoke.json"
foreach ($target in @($enterpriseResult, $agentResult, $criticResult, $apiResult)) {
    if (Test-Path -LiteralPath $target) {
        throw "Results already exist at $target. Use a new ResultPrefix to preserve earlier runs."
    }
}
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:TECHQA_PROFILE = 'full'
$env:TECHQA_DENSE_BACKEND = 'semantic'
$env:TECHQA_RERANKER = 'nomic'
$env:AGENT_PROFILE = 'ollama'
$env:AGENT_RETRIEVAL_BACKEND = 'techqa'
$env:MODEL_PROVIDER = 'ollama'
$env:RAG_BACKEND = 'techqa'
$failedStages = [System.Collections.Generic.List[string]]::new()
Push-Location -LiteralPath $projectRoot
try {
    & (Join-Path $PSScriptRoot 'start-local.ps1') -FullTechQA
    & $pythonPath (Join-Path $PSScriptRoot 'prepare_techqa_regression.py')
    if ($LASTEXITCODE -ne 0) { throw 'Regression snapshots differ from original TechQA.' }
    Push-Location -LiteralPath (Join-Path $projectRoot 'enterprise-ai-agent')
    try {
        $stageCode = Invoke-PythonCheck -PythonArgs @('-m', 'evaluation.evaluate', '--dataset', '../data/techqa/regression/questions.json', '--output', $enterpriseResult) -LogPath (Join-Path $projectRoot "audit/${ResultPrefix}_enterprise.log")
        if ($stageCode -ne 0) { $failedStages.Add('Enterprise regression') }
    } finally { Pop-Location }
    Push-Location -LiteralPath (Join-Path $projectRoot 'agentic-rag-homework')
    try {
        $stageCode = Invoke-PythonCheck -PythonArgs @('-m', 'evaluation.run', '--provider', 'ollama', '--planner-runs', '10', '--output', $agentResult) -LogPath (Join-Path $projectRoot "audit/${ResultPrefix}_agents.log")
        if ($stageCode -ne 0) { $failedStages.Add('Agent comparison') }
        $stageCode = Invoke-PythonCheck -PythonArgs @('-m', 'evaluation.critic_stability', '--evidence-mode', 'retrieved', '--split', 'fixture', '--label', 'all', '--limit', '15', '--repeats', '2', '--output', $criticResult) -LogPath (Join-Path $projectRoot "audit/${ResultPrefix}_critic.log")
        if ($stageCode -ne 0) { $failedStages.Add('Critic stability') }
    } finally { Pop-Location }
    $stageCode = Invoke-PythonCheck -PythonArgs @((Join-Path $PSScriptRoot 'smoke_techqa.py'), '--output', $apiResult) -LogPath (Join-Path $projectRoot "audit/${ResultPrefix}_api.log")
    if ($stageCode -ne 0) { $failedStages.Add('HTTP smoke') }
    $stageCode = Invoke-PythonCheck -PythonArgs @((Join-Path $PSScriptRoot 'test_all.py')) -LogPath (Join-Path $projectRoot "audit/${ResultPrefix}_pytest.txt")
    if ($stageCode -ne 0) { $failedStages.Add('Pytest') }
} finally { Pop-Location }
if ($failedStages.Count) { throw ('Failed stages: ' + ($failedStages -join ', ')) }
Write-Host "TechQA workflow checks completed: $ResultPrefix. These are workflow checks, not production-quality sign-off."
