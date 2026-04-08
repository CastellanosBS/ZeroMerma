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
  Invoke-ZeroMermaApiMigrations
  Invoke-ZeroMermaApiSeedLocalData
}
finally {
  Pop-Location
}
