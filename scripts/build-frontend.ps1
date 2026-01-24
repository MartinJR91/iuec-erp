param(
    [string]$FrontendPath = ".\frontend",
    [string]$BackendStaticPath = ".\backend\static\react"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Build React"
Push-Location $FrontendPath
npm install
if ($LASTEXITCODE -ne 0) {
    throw "npm install failed"
}
npm run build
if ($LASTEXITCODE -ne 0) {
    throw "npm run build failed"
}
Pop-Location

Write-Host "==> Copy build to backend static"
if (Test-Path $BackendStaticPath) {
    Remove-Item -Recurse -Force $BackendStaticPath
}
New-Item -ItemType Directory -Force $BackendStaticPath | Out-Null
Copy-Item -Recurse -Force (Join-Path $FrontendPath "build\*") $BackendStaticPath

Write-Host "==> Done"
