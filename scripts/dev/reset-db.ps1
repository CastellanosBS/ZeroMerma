param(
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$ToolsScript = Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1"
. $ToolsScript
$Root = Get-ZeroMermaRepoRoot

if (-not $Force) {
  throw "This resets the local PostgreSQL volume. Re-run with -Force to continue."
}

Push-Location $Root
try {
  Invoke-ZeroMermaDockerCompose down --volumes --remove-orphans
  Invoke-ZeroMermaUv sync --all-packages --dev
  Start-ZeroMermaPostgres
  Wait-ZeroMermaPostgres
  Invoke-ZeroMermaUv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
}
finally {
  Pop-Location
}
