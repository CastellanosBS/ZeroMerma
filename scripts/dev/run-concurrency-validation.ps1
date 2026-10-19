[CmdletBinding()]
param(
  [ValidateSet('All', 'Commands', 'Cash', 'Inventory')]
  [string]$Suite = 'All'
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../powershell/ZeroMerma.Tools.ps1')
. (Join-Path $PSScriptRoot '../powershell/ZeroMerma.TestDatabase.ps1')
. (Join-Path $PSScriptRoot '../powershell/ZeroMerma.ValidationArtifacts.ps1')
$root = Get-ZeroMermaRepoRoot
$runId = [Guid]::NewGuid().ToString('N')
$evidence = Join-Path $root ".tmp/validation/concurrency/$runId"
$published = Join-Path $root ".tmp/validation-published/concurrency/$runId"
$null = New-Item -ItemType Directory -Path $evidence -Force
$targets = [ordered]@{
  Commands = 'apps/api/tests/test_command_concurrency.py'
  Cash = 'apps/api/tests/test_cash_concurrency.py'
  Inventory = 'apps/api/tests/test_inventory_concurrency.py'
}
$selected = if ($Suite -eq 'All') { @($targets.Values) } else { @($targets[$Suite]) }
$started = [DateTime]::UtcNow
$passed = $false
Push-Location $root
try {
  Invoke-ZeroMermaIsolatedDatabase -RunId $runId -Action {
    $arguments = @('run', '--frozen', 'pytest') + $selected + @(
      "--junitxml=$evidence/concurrency.xml", '-o', 'junit_logging=all',
      '-o', 'junit_log_passing_tests=true'
    )
    $exitCode = Invoke-ZeroMermaProtectedValidationProcess -FilePath (Resolve-ZeroMermaUvPath) `
      -ArgumentList $arguments -CaptureDirectory (Join-Path $root '.tmp/validation-private')
    if ($exitCode -ne 0) { throw "Concurrency validation failed with exit code $exitCode." }
  }
  $passed = $true
}
finally {
  [ordered]@{
    suite = $Suite
    targets = $selected
    passed = $passed
    started_at = $started.ToString('o')
    finished_at = [DateTime]::UtcNow.ToString('o')
    commit = (& git rev-parse HEAD)
    working_tree_clean = (@(& git status --porcelain).Count -eq 0)
  } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'result.json')
  Protect-ZeroMermaValidationArtifacts -SourceDirectory $evidence -DestinationDirectory $published
  Write-Host "Published concurrency evidence: $published"
  Pop-Location
}
