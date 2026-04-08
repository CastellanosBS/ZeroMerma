param()

$ErrorActionPreference = "Stop"
$ToolsScript = Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1"
. $ToolsScript
$Root = Get-ZeroMermaRepoRoot

Push-Location $Root
try {
  Invoke-ZeroMermaUv run --project apps/api python -m zeromerma_api.presentation.openapi packages/api-client/openapi.json
  Invoke-ZeroMermaPnpm --filter @zeromerma/api-client generate:types
}
finally {
  Pop-Location
}
