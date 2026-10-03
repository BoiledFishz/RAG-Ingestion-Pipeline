param(
    [switch]$WaitForIndex,
    [switch]$Resume,
    [string]$EnterpriseOutput = 'evaluation/results/techqa_semantic_v3'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $projectRoot '.venv312\Scripts\python.exe'
}
$manifestPath = Join-Path $projectRoot '.rag_data\techqa_semantic\manifest.json'
while (-not (Test-Path -LiteralPath $manifestPath)) {
    if (-not $WaitForIndex) { throw 'Complete the semantic build before running acceptance.' }
    Start-Sleep -Seconds 30
}
$env:TECHQA_PROFILE = 'full'
$env:TECHQA_DENSE_BACKEND = 'semantic'
$env:TECHQA_RERANKER = 'nomic'
$env:AGENT_PROFILE = 'ollama'
$env:AGENT_RETRIEVAL_BACKEND = 'techqa'
$env:MODEL_PROVIDER = 'ollama'
$env:RAG_BACKEND = 'techqa'
& (Join-Path $PSScriptRoot 'start-local.ps1') -FullTechQA
Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $projectRoot 'evals/techqa_semantic_manifest.json')
$trainResumeArgs = @()
if ($Resume -and (Test-Path 'evals/techqa_semantic_calibration/run_config.json')) { $trainResumeArgs = @('--resume') }
& $pythonPath -m rag.techqa.evaluate --split train --output evals/techqa_semantic_calibration @trainResumeArgs
if ($LASTEXITCODE -ne 0) { throw 'Official full-training semantic retrieval evaluation failed.' }
& $pythonPath -m rag.techqa.calibrate --input evals/techqa_semantic_calibration
if ($LASTEXITCODE -ne 0) { throw 'Training-only relevance calibration failed.' }
$devResumeArgs = @()
if ($Resume -and (Test-Path 'evals/techqa_semantic_full/run_config.json')) { $devResumeArgs = @('--resume') }
& $pythonPath -m rag.techqa.evaluate --split dev --output evals/techqa_semantic_full @devResumeArgs
if ($LASTEXITCODE -ne 0) { throw 'Official full-development semantic retrieval evaluation failed.' }
$validationResumeArgs = @()
if ($Resume -and (Test-Path 'evals/techqa_semantic_validation/run_config.json')) { $validationResumeArgs = @('--resume') }
& $pythonPath -m rag.techqa.evaluate --split validation --output evals/techqa_semantic_validation @validationResumeArgs
if ($LASTEXITCODE -ne 0) { throw 'Official validation semantic retrieval evaluation failed.' }
Push-Location -LiteralPath (Join-Path $projectRoot 'enterprise-ai-agent')
try {
    $enterpriseResumeArgs = @()
    $enterpriseConfig = Join-Path $EnterpriseOutput 'run_config.json'
    $enterpriseProgress = Join-Path $EnterpriseOutput 'progress.jsonl'
    if ($Resume -and (Test-Path -LiteralPath $enterpriseConfig) -and
        (Test-Path -LiteralPath $enterpriseProgress) -and
        (Get-Item -LiteralPath $enterpriseProgress).Length -gt 0) {
        $enterpriseResumeArgs = @('--resume')
    }
    & $pythonPath -m evaluation.evaluate --output $EnterpriseOutput @enterpriseResumeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Enterprise official dev evaluation failed.' }
} finally { Pop-Location }
& (Join-Path $PSScriptRoot 'run-agent-acceptance.ps1')
Write-Host 'Semantic and Agent acceptance runs completed; inspect actual metrics before signing off.'
