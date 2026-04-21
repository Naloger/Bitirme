Param(
    [switch]$Install
)

# install_spacy_models.ps1
# Usage:
#  - Dry run (default): .\scripts\install_spacy_models.ps1
#  - Perform install: .\scripts\install_spacy_models.ps1 -Install

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptRoot

$venvPath = Join-Path $ScriptRoot '..\.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$actions = @()

$actions += "Ensure Python is available as 'python' on PATH"
$actions += "Create virtualenv at $venvPath if it does not exist"
$actions += "Upgrade pip inside venv"
$actions += "Install spaCy into venv"
$actions += "Install stanza and nltk into venv"
$actions += "Download spaCy models: en_core_web_sm, tr_core_news_sm into venv"
$actions += "Run additional model downloads (stanza tr model, nltk corpora)"

Write-Host "Planned actions:`n"
$actions | ForEach-Object { Write-Host " - $_" }

if (-not $Install) {
    Write-Host "`nDry run complete. To perform installation, re-run with -Install:`n   .\scripts\install_spacy_models.ps1 -Install" -ForegroundColor Yellow
    exit 0
}

# Real install steps
try {
    # 1) Create venv if missing
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating virtual environment at $venvPath..."
        & python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
    } else {
        Write-Host "Virtual environment already exists: $venvPath"
    }

    # Use venv's python for subsequent commands
    if (-not (Test-Path $venvPython)) { throw "Python executable not found in venv: $venvPython" }

    Write-Host "Upgrading pip..."
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

    Write-Host "Installing spaCy..."
    & $venvPython -m pip install -U spacy
    if ($LASTEXITCODE -ne 0) { throw "spaCy installation failed" }
    Write-Host "Installing stanza and nltk..."
    & $venvPython -m pip install -U stanza nltk
    if ($LASTEXITCODE -ne 0) { Write-Host "Warning: stanza/nltk installation may have failed" -ForegroundColor Yellow }

    Write-Host "Downloading models (en_core_web_sm)..."
    & $venvPython -m spacy download en_core_web_sm
    if ($LASTEXITCODE -ne 0) { Write-Host "Warning: en_core_web_sm download failed" -ForegroundColor Yellow }

    Write-Host "Downloading models (tr_core_news_sm)..."
    & $venvPython -m spacy download tr_core_news_sm
    if ($LASTEXITCODE -ne 0) { Write-Host "Warning: tr_core_news_sm download failed" -ForegroundColor Yellow }

    Write-Host "Running additional model downloads (stanza, nltk corpora)..."
    $installScript = Join-Path $ScriptRoot 'install_models.py'
    if (Test-Path $installScript) {
        & $venvPython $installScript
        if ($LASTEXITCODE -ne 0) { Write-Host "Warning: some model downloads failed (see output)" -ForegroundColor Yellow }
    } else {
        Write-Host "Warning: install_models.py not found at $installScript" -ForegroundColor Yellow
    }

    Write-Host "Installation complete. To use the venv in PowerShell run:`n  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "Error during installation: $_" -ForegroundColor Red
    exit 1
}

