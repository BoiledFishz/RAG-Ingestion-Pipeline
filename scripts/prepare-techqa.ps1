param([string]$Python = '.venv312\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = if ([System.IO.Path]::IsPathRooted($Python)) { $Python } else {
    Join-Path $projectRoot $Python
}
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the Python 3.12 environment first (README).' }
Push-Location -LiteralPath (Join-Path $projectRoot 'enterprise-ai-agent')
try {
    & $pythonPath -c 'import logging; from vectorstore.techqa import download_archive, extract_archive; logging.basicConfig(level=logging.INFO); extract_archive(download_archive(), scope="full")'
    if ($LASTEXITCODE -ne 0) { throw 'Official TechQA acquisition/verification failed.' }
} finally { Pop-Location }
& $pythonPath -m rag.techqa.index --scope full
if ($LASTEXITCODE -ne 0) { throw 'Full BM25 construction failed.' }
& $pythonPath -m rag.techqa.semantic --download-model
if ($LASTEXITCODE -ne 0) { throw 'Pinned semantic encoder acquisition failed.' }
& $pythonPath -m rag.techqa.semantic
if ($LASTEXITCODE -ne 0) { throw 'Full semantic construction failed; rerun to resume.' }
Write-Host 'Full official TechQA preparation complete. Start with scripts/start-local.ps1 -FullTechQA.'
