[CmdletBinding()]
param(
  [string[]]$TestTarget = @(),
  [string]$RunId
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.TestDatabase.ps1")
Invoke-ZeroMermaIsolatedDatabase -RunId $RunId -Action {
  # No targets means every suite declared by pyproject.toml is discovered.
  Invoke-ZeroMermaUv run --frozen pytest @TestTarget
}
