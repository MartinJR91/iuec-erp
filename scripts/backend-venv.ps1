param(
    [string]$BackendPath = ".\backend"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Backend venv setup"
Push-Location $BackendPath

if (-not (Test-Path ".\.venv")) {
    py -3.12 -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt

Write-Host "==> Ready"
Pop-Location
