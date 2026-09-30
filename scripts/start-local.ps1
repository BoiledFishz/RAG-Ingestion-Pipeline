param([switch]$FullTechQA)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaPath = if ($ollamaCommand) { $ollamaCommand.Source } else {
    Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
}
if (-not (Test-Path -LiteralPath $ollamaPath)) { throw 'Install Ollama first.' }
try { Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 3 | Out-Null }
catch {
    Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw 'Ollama did not become ready on port 11434.' }
}
$availableModels = (Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 5).models.name
foreach ($model in @('llama3.2:3b', 'nomic-embed-text')) {
    if ($model -in $availableModels -or "${model}:latest" -in $availableModels) { continue }
    & $ollamaPath pull $model
    if ($LASTEXITCODE -ne 0) { throw "Could not download $model" }
}

if ($FullTechQA) {
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = 'python' }
    & $pythonPath (Join-Path $PSScriptRoot 'start_qdrant.py')
    if ($LASTEXITCODE -ne 0) { throw 'Qdrant startup failed. See the logged failing stage.' }
    $env:AGENT_PROFILE = 'offline'
    $env:AGENT_EMBEDDING_PROVIDER = 'hash'
    $env:AGENT_QDRANT_URL = 'http://127.0.0.1:6333'
    $env:AGENT_COLLECTION = 'techqa_full_hash'
    Write-Host 'TechQA Qdrant is ready. After seeding, run python -m vectorstore.indexes in enterprise-ai-agent.'
}
Write-Host 'Models are ready. Run python main.py data/aws_support_test_corpus/data, then rag-api.'
