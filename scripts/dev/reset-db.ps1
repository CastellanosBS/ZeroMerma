param(
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$ToolsScript = Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1"
. $ToolsScript
$Root = Get-ZeroMermaRepoRoot
$ToolchainScript = Join-Path $PSScriptRoot "check-toolchain.ps1"

if (-not $Force) {
  throw "This resets the local PostgreSQL volume. Re-run with -Force to continue."
}

Push-Location $Root
try {
  & $ToolchainScript
  Invoke-ZeroMermaDockerCompose down --volumes --remove-orphans
  Invoke-ZeroMermaUv sync --all-packages --dev --frozen
  Start-ZeroMermaPostgres
  Wait-ZeroMermaPostgres
  Invoke-ZeroMermaApiMigrations
  Invoke-ZeroMermaApiSeedLocalData
}
finally {
  Pop-Location
}
