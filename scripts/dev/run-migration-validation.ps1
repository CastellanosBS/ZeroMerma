[CmdletBinding()]
param(
  [ValidateSet("Fast", "Full")]
  [string]$Mode = "Fast"
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1")

$repoRoot = Get-ZeroMermaRepoRoot
$toolchainScript = Join-Path $PSScriptRoot "check-toolchain.ps1"
$apiTestScript = Join-Path $PSScriptRoot "run-api-tests.ps1"
$migrationTests = "apps/api/migration_tests/test_migration_validation.py"

$testTargets = if ($Mode -eq "Full") {
  @($migrationTests, "-s")
}
else {
  @(
    "${migrationTests}::test_static_graph",
    "${migrationTests}::test_fresh_schema_drift_and_seed",
    "-s"
  )
}

Push-Location $repoRoot
try {
  $powerShellPath = (Get-Process -Id $PID).Path
  & $powerShellPath -NoProfile -File $toolchainScript
  if ($LASTEXITCODE -ne 0) {
    throw "Canonical toolchain preflight failed."
  }

  Write-Host "Running $Mode Alembic validation through the protected ephemeral database harness..."
  & $apiTestScript -TestTarget $testTargets
  if ($LASTEXITCODE -ne 0) {
    throw "$Mode Alembic validation failed."
  }
  Write-Host "$Mode Alembic validation completed successfully."
}
finally {
  Pop-Location
}
