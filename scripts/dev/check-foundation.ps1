[CmdletBinding()]
param(
  [ValidateSet("All", "Preflight", "Backend", "Worker", "Migrations", "Contracts", "Web", "Browser", "Negative")]
  [string]$Stage = "All"
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1")
$root = Get-ZeroMermaRepoRoot
$runId = [Guid]::NewGuid().ToString("N")
$evidenceDirectory = Join-Path $root ".tmp/validation/foundation/$runId"
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
$stages = if ($Stage -eq "All") {
  @("Preflight", "Backend", "Worker", "Migrations", "Contracts", "Web", "Browser", "Negative")
} else { @($Stage) }

Push-Location $root
try {
  foreach ($currentStage in $stages) {
    $started = [DateTime]::UtcNow
    $passed = $false
    Start-Transcript -Path (Join-Path $evidenceDirectory "$currentStage.log") | Out-Null
    try {
      & (Join-Path $PSScriptRoot "check-toolchain.ps1")
      switch ($currentStage) {
        "Preflight" {
          Invoke-ZeroMermaUv sync --all-packages --dev --frozen
          Invoke-ZeroMermaPnpm install --frozen-lockfile
          $dockerType = & docker info --format '{{.OSType}}'
          if ($LASTEXITCODE -ne 0 -or $dockerType -ne "linux") {
            throw "Foundation validation requires the Linux Docker engine"
          }
        }
        "Backend" {
          Invoke-ZeroMermaUv run --frozen python -m compileall -q apps/api/src
          Invoke-ZeroMermaUv run --frozen ruff check .
          Invoke-ZeroMermaUv run --frozen mypy apps/api/src apps/worker/src
          & (Join-Path $PSScriptRoot "run-api-tests.ps1") -TestTarget @(
            "apps/api/tests", "apps/api/unit_tests",
            "--junitxml=$evidenceDirectory/backend.xml"
          )
        }
        "Worker" {
          Invoke-ZeroMermaUv run --frozen python -m compileall -q apps/worker/src
          Invoke-ZeroMermaUv run --frozen pytest apps/worker/tests "--junitxml=$evidenceDirectory/worker-unit.xml"
          & (Join-Path $PSScriptRoot "run-api-tests.ps1") -TestTarget @(
            "apps/worker/integration_tests", "--junitxml=$evidenceDirectory/worker-postgres.xml"
          )
          Invoke-ZeroMermaUv run --frozen --project apps/worker python -m zeromerma_worker --once --skip-db-check
        }
        "Migrations" {
          & (Join-Path $PSScriptRoot "run-migration-validation.ps1") -Mode Full
        }
        "Contracts" {
          Invoke-ZeroMermaUv run --frozen python scripts/dev/check-functional-operation-matrix.py
          Invoke-ZeroMermaPnpm contracts:check
          Invoke-ZeroMermaUv run --frozen pytest scripts/dev/tests/test_api_contracts.py scripts/dev/tests/test_functional_operation_matrix.py "--junitxml=$evidenceDirectory/contracts.xml"
        }
        "Web" {
          Invoke-ZeroMermaPnpm lint
          Invoke-ZeroMermaPnpm typecheck
          Invoke-ZeroMermaPnpm test
          Invoke-ZeroMermaPnpm build
          Invoke-ZeroMermaPnpm test:e2e
        }
        "Browser" {
          & (Join-Path $PSScriptRoot "run-web-integration.ps1") -Surface All
        }
        "Negative" {
          Invoke-ZeroMermaUv run --frozen pytest scripts/dev/tests/test_foundation_gates.py "--junitxml=$evidenceDirectory/negative-gates.xml"
        }
      }
      $passed = $true
    }
    finally {
      Stop-Transcript | Out-Null
      $result = [ordered]@{
        stage = $currentStage
        passed = $passed
        started_at = $started.ToString("o")
        finished_at = [DateTime]::UtcNow.ToString("o")
        commit = (& git rev-parse HEAD)
        working_tree_clean = (@(& git status --porcelain).Count -eq 0)
        artifact_sha256 = [ordered]@{}
      }
      foreach ($artifact in @(
        "uv.lock", "pnpm-lock.yaml", "packages/api-client/openapi.json",
        "packages/api-client/src/generated/schema.ts", "docs/architecture/API_CONTRACT_INVENTORY.json"
      )) {
        $result.artifact_sha256[$artifact] = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
      }
      $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDirectory "$currentStage.json")
    }
  }
  Write-Host "Foundation validation passed. Evidence: $evidenceDirectory"
}
finally { Pop-Location }
