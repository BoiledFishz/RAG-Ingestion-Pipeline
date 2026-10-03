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
    New-Item -ItemType Directory -Path (Join-Path $projectRoot '.rag_data') -Force | Out-Null
    Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $projectRoot '.rag_data\ollama-server.stdout.log') `
        -RedirectStandardError (Join-Path $projectRoot '.rag_data\ollama-server.stderr.log')
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 3 }
    }
    if (-not $ready) { throw 'Ollama did not become ready on port 11434.' }
}
$availableModels = (Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 5).models.name
foreach ($model in @('qwen2.5:7b', 'llama3.2:3b', 'nomic-embed-text')) {
    if ($model -in $availableModels -or "${model}:latest" -in $availableModels) { continue }
    & $ollamaPath pull $model
    if ($LASTEXITCODE -ne 0) { throw "Could not download $model" }
}

if ($FullTechQA) {
    $pythonPath = Join-Path $projectRoot '.venv312\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = 'python' }
    $manifestPath = Join-Path $projectRoot '.rag_data\techqa_semantic\manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw 'Build the full semantic index first: python -m rag.techqa.semantic (see README).'
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if (-not $manifest.complete -or $manifest.scope -ne 'full') {
        throw 'The default service requires a complete full-corpus semantic index.'
    }
    try { Invoke-RestMethod 'http://127.0.0.1:11435/healthz' -TimeoutSec 5 | Out-Null }
    catch {
        Start-Process -FilePath $pythonPath -ArgumentList @(
            '-m', 'uvicorn', 'rag.techqa.embedding_server:app',
            '--host', '127.0.0.1', '--port', '11435'
        ) -WorkingDirectory $projectRoot -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $projectRoot '.rag_data\semantic-server.stdout.log') `
            -RedirectStandardError (Join-Path $projectRoot '.rag_data\semantic-server.stderr.log')
        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                Invoke-RestMethod 'http://127.0.0.1:11435/healthz' -TimeoutSec 5 | Out-Null
                $ready = $true
                break
            } catch { Start-Sleep -Seconds 1 }
        }
        if (-not $ready) { throw 'Semantic search startup failed; inspect .rag_data/semantic-server.stderr.log.' }
    }
    $env:TECHQA_DENSE_BACKEND = 'semantic'
    $env:AGENT_PROFILE = 'ollama'
    Write-Host 'Full TechQA semantic search is ready on port 11435.'
}
Write-Host 'Models are ready. Run python main.py for the official TechQA format fixture.'
Write-Host 'Full API: start the semantic search service with -FullTechQA, then run rag-api.'
