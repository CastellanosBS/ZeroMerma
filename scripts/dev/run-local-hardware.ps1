[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PairingKeyFile,
  [Parameter(Mandatory = $true)][string]$Spool,
  [Parameter(Mandatory = $true)][string]$PosOrigin
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1")
$keyPath = (Resolve-Path -LiteralPath $PairingKeyFile).Path
$spoolPath = [System.IO.Path]::GetFullPath($Spool)
if (-not (Test-Path -LiteralPath ([System.IO.Path]::GetDirectoryName($spoolPath)) -PathType Container)) {
  throw "The private local spool directory must already exist."
}
$originUri = [Uri]$PosOrigin
if ($originUri.Scheme -notin @("http", "https") -or $originUri.AbsolutePath -ne "/" -or $originUri.Query -or $originUri.Fragment -or $originUri.UserInfo) {
  throw "PosOrigin must be one exact HTTP(S) origin without a path, query, or fragment."
}
$normalizedOrigin = $originUri.GetLeftPart([System.UriPartial]::Authority)
Write-Output "Diagnostic local bridge: no physical adapters are installed or certified."
Push-Location (Get-ZeroMermaRepoRoot)
try {
  Invoke-ZeroMermaUv run --frozen python -m zeromerma_api.local_hardware `
    --pairing-key-file $keyPath --spool $spoolPath --pos-origin $normalizedOrigin
} finally {
  Pop-Location
}
