param()

$ErrorActionPreference = "Stop"
$ToolsScript = Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1"
. $ToolsScript

$Root = Get-ZeroMermaRepoRoot
$ToolchainScript = Join-Path $PSScriptRoot "check-toolchain.ps1"
& $ToolchainScript
$SafeRoot = $Root.Replace("'", "''")
$UvCommand = Get-ZeroMermaUvCommandExpression
$PnpmCommand = Get-ZeroMermaPnpmCommandExpression

function Start-ZeroMermaProcess {
  param(
    [string]$Title,
    [string]$Command
  )

  Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "Set-Location -LiteralPath '$SafeRoot'; `$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
  )
}

Push-Location $Root
try {
  Write-Host "Bootstrapping Python workspace with uv..."
  Invoke-ZeroMermaUv sync --all-packages --dev --frozen

  Write-Host "Installing Node workspace dependencies..."
  Invoke-ZeroMermaPnpm install --frozen-lockfile

  Write-Host "Generating frontend API contracts from backend OpenAPI..."
  Invoke-ZeroMermaPnpm contracts:generate

  Start-ZeroMermaPostgres
  Wait-ZeroMermaPostgres

  Write-Host "Applying database migrations..."
  Invoke-ZeroMermaApiMigrations

  Write-Host "Seeding local development data..."
  Invoke-ZeroMermaApiSeedLocalData

  Start-ZeroMermaProcess `
    -Title "ZeroMerma API" `
    -Command "$UvCommand run --project apps/api uvicorn zeromerma_api.main:create_app --factory --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000"
  Start-ZeroMermaProcess `
    -Title "ZeroMerma Worker" `
    -Command "$UvCommand run --project apps/worker python -m zeromerma_worker"
  Start-ZeroMermaProcess `
    -Title "ZeroMerma POS Web" `
    -Command "$PnpmCommand --filter @zeromerma/pos-web dev"
  Start-ZeroMermaProcess `
    -Title "ZeroMerma Backoffice Web" `
    -Command "$PnpmCommand --filter @zeromerma/backoffice-web dev"

  Write-Host "ZeroMerma local processes are starting."
  Write-Host "API: http://localhost:8000"
  Write-Host "POS web: http://localhost:5173"
  Write-Host "Backoffice web: http://localhost:5174"
}
finally {
  Pop-Location
}
