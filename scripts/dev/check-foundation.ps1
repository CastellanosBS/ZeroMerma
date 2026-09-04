param(
  [switch]$CiIsolated
)

$ErrorActionPreference = "Stop"
$ToolsScript = Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1"
. $ToolsScript

$Root = Get-ZeroMermaRepoRoot
$ToolchainScript = Join-Path $PSScriptRoot "check-toolchain.ps1"
$ApiTestScript = Join-Path $PSScriptRoot "run-api-tests.ps1"
$MigrationValidationScript = Join-Path $PSScriptRoot "run-migration-validation.ps1"
$FunctionalOperationMatrixScript = Join-Path $PSScriptRoot "check-functional-operation-matrix.py"

function Test-ZeroMermaHttpServer {
  param(
    [string]$Name,
    [scriptblock]$ScriptBlock,
    [object[]]$ArgumentList,
    [string]$Url,
    [int]$Attempts = 40,
    [int]$DelayMilliseconds = 500
  )

  Write-Host "Checking $Name at $Url..."
  $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList

  try {
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
      Start-Sleep -Milliseconds $DelayMilliseconds

      if ($job.State -eq "Failed") {
        Receive-Job $job | Write-Host
        throw "$Name process failed before responding at $Url."
      }

      try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
          Write-Host "$Name responded successfully."
          return
        }
      }
      catch {
      }
    }

    Receive-Job $job | Write-Host
    throw "$Name did not respond at $Url. Check whether the port is available and rerun this script from the repository root."
  }
  finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
  }
}

Push-Location $Root
try {
  & $ToolchainScript

  Write-Host "Resolving required tools..."
  $UvPath = Resolve-ZeroMermaUvPath
  $Pnpm = Resolve-ZeroMermaPnpmCommand
  $null = Resolve-ZeroMermaDockerPath

  Write-Host "Bootstrapping Python workspace with uv..."
  Invoke-ZeroMermaUv sync --all-packages --dev --frozen

  Write-Host "Validating the functional operation matrix without database access..."
  Invoke-ZeroMermaUv run --frozen python $FunctionalOperationMatrixScript

  Write-Host "Installing Node workspace dependencies..."
  Invoke-ZeroMermaPnpm install --frozen-lockfile

  if (-not $CiIsolated) {
    Write-Host "Validating Docker Compose configuration..."
    Invoke-ZeroMermaDockerCompose config
    Start-ZeroMermaPostgres
    Wait-ZeroMermaPostgres

    Write-Host "Applying database migrations to the local development database..."
    Invoke-ZeroMermaApiMigrations

    Write-Host "Seeding local development data..."
    Invoke-ZeroMermaApiSeedLocalData
  }

  Write-Host "Running Python validation..."
  Invoke-ZeroMermaUv run ruff check apps/api/src apps/api/tests apps/api/unit_tests apps/worker/src apps/worker/tests
  Invoke-ZeroMermaUv run mypy apps/api/src apps/worker/src
  Invoke-ZeroMermaUv run --frozen pytest apps/api/unit_tests/test_database_safety.py
  & $ApiTestScript
  & $MigrationValidationScript -Mode Fast

  Write-Host "Verifying worker bootability without database access..."
  Invoke-ZeroMermaUv run --project apps/worker python -m zeromerma_worker --once --skip-db-check

  Write-Host "Generating API client contracts..."
  Invoke-ZeroMermaPnpm contracts:generate

  Write-Host "Running frontend validation..."
  Invoke-ZeroMermaPnpm lint
  Invoke-ZeroMermaPnpm test
  Invoke-ZeroMermaPnpm build

  if (-not $CiIsolated) {
    Write-Host "Verifying worker bootability against PostgreSQL..."
    Invoke-ZeroMermaUv run --project apps/worker python -m zeromerma_worker --once

    Test-ZeroMermaHttpServer `
      -Name "API health endpoint" `
      -Url "http://127.0.0.1:18000/health" `
      -ScriptBlock {
        param($RootPath, $UvExecutable)
        Set-Location -LiteralPath $RootPath
        & $UvExecutable run --project apps/api uvicorn zeromerma_api.main:create_app --factory --app-dir apps/api/src --host 127.0.0.1 --port 18000
      } `
      -ArgumentList @($Root, $UvPath)
  }

  Test-ZeroMermaHttpServer `
    -Name "POS web app" `
    -Url "http://127.0.0.1:15173" `
    -ScriptBlock {
      param($RootPath, $PnpmExecutable, $PnpmBaseArguments)
      Set-Location -LiteralPath $RootPath
      $arguments = @()
      $arguments += $PnpmBaseArguments
      $arguments += @("--filter", "@zeromerma/pos-web", "exec", "vite", "--host", "127.0.0.1", "--port", "15173", "--strictPort")
      & $PnpmExecutable @arguments
    } `
    -ArgumentList @($Root, $Pnpm.Path, $Pnpm.Arguments)

  Test-ZeroMermaHttpServer `
    -Name "Backoffice web app" `
    -Url "http://127.0.0.1:15174" `
    -ScriptBlock {
      param($RootPath, $PnpmExecutable, $PnpmBaseArguments)
      Set-Location -LiteralPath $RootPath
      $arguments = @()
      $arguments += $PnpmBaseArguments
      $arguments += @("--filter", "@zeromerma/backoffice-web", "exec", "vite", "--host", "127.0.0.1", "--port", "15174", "--strictPort")
      & $PnpmExecutable @arguments
    } `
    -ArgumentList @($Root, $Pnpm.Path, $Pnpm.Arguments)

  Write-Host "Foundation validation completed successfully."
}
finally {
  Pop-Location
}
