[CmdletBinding()]
param(
  [switch]$StartPostgres,
  [switch]$ApplyMigrations,
  [switch]$SeedLocalData,
  [switch]$SkipBackend,
  [switch]$SkipBuild,
  [switch]$SkipContracts,
  [switch]$SkipFrontendUnit,
  [switch]$SkipLint,
  [switch]$SkipPlaywright
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1")

$repoRoot = Get-ZeroMermaRepoRoot
$posWebRoot = Join-Path $repoRoot "apps\pos-web"
$apiTestScript = Join-Path $PSScriptRoot "run-api-tests.ps1"

$playwrightSpecs = @(
  "e2e/pos-entry.spec.ts",
  "e2e/operational-regression.spec.ts"
)

$frontendRegressionSpecs = @(
  "src/features/cash-session-open/cash-session-open-form.test.tsx",
  "src/features/pos-terminal/pos-terminal-workspace.test.tsx",
  "src/features/pos-terminal/pos-checkout-panel.test.tsx",
  "src/features/tickets/tickets-screen.test.tsx",
  "src/features/returns/returns-screen.test.tsx",
  "src/features/operations/operation-module-screen.test.tsx",
  "src/features/transfers/dispatch-screen.test.tsx",
  "src/features/transfers/receipt-screen.test.tsx",
  "src/features/corrections/corrections-screen.test.tsx",
  "src/features/orders/orders-screen.test.tsx",
  "src/features/payments/payments-screen.test.tsx",
  "src/features/discounts/discounts-screen.test.tsx",
  "src/features/cash-close/cash-close-screen.test.tsx"
)

$backendRegressionTests = @(
  "apps/api/tests/test_phase_1a_pos_bootstrap.py",
  "apps/api/tests/test_phase_2a_pos_sales.py",
  "apps/api/tests/test_tickets_module.py",
  "apps/api/tests/test_returns_module.py",
  "apps/api/tests/test_phase_3a_operations.py",
  "apps/api/tests/test_phase_4a_corrections.py",
  "apps/api/tests/test_orders_module.py",
  "apps/api/tests/test_payments_module.py",
  "apps/api/tests/test_discounts_module.py",
  "apps/api/tests/test_phase_7a_cash_close.py",
  "apps/api/tests/test_phase_7b_cash_close.py",
  "apps/api/tests/test_dev_audit_snapshot.py"
)

if ($StartPostgres) {
  Start-ZeroMermaPostgres
  Wait-ZeroMermaPostgres
}

if ($ApplyMigrations) {
  Invoke-ZeroMermaApiMigrations
}

if ($SeedLocalData) {
  Invoke-ZeroMermaApiSeedLocalData
}

if (-not $SkipContracts) {
  Write-Host "Generating API contracts..."
  Invoke-ZeroMermaPnpm contracts:generate
}

Push-Location $posWebRoot
try {
  if (-not $SkipPlaywright) {
    Write-Host "Running Playwright operational smoke..."
    Invoke-ZeroMermaPnpm exec playwright test @playwrightSpecs
  }

  if (-not $SkipFrontendUnit) {
    Write-Host "Running frontend operational regression tests..."
    Invoke-ZeroMermaPnpm exec vitest run @frontendRegressionSpecs --reporter=dot
  }

  if (-not $SkipLint) {
    Write-Host "Running POS lint and typecheck..."
    Invoke-ZeroMermaPnpm lint
    Invoke-ZeroMermaPnpm typecheck
  }

  if (-not $SkipBuild) {
    Write-Host "Running POS build..."
    Invoke-ZeroMermaPnpm build
  }
}
finally {
  Pop-Location
}

if (-not $SkipBackend) {
  Write-Host "Running backend operational persistence regression tests in isolated PostgreSQL..."
  & $apiTestScript -TestTarget $backendRegressionTests
}
