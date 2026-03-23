param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "help",
        "install",
        "precommit",
        "db-check",
        "db-upgrade",
        "seed-core",
        "seed-dev",
        "seed-inventory-fixture",
        "format",
        "lint",
        "test",
        "test-pos",
        "smoke",
        "ci-local"
    )]
    [string]$Task = "help"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    Write-Host ""
    Write-Host ">> $Command" -ForegroundColor Cyan
    Invoke-Expression $Command
}

function Show-Help {
    Write-Host ""
    Write-Host "ZeroMerma Backend - Official PowerShell Tasks" -ForegroundColor Green
    Write-Host ""
    Write-Host "  .\tasks.ps1 help"
    Write-Host "  .\tasks.ps1 install"
    Write-Host "  .\tasks.ps1 precommit"
    Write-Host "  .\tasks.ps1 db-check"
    Write-Host "  .\tasks.ps1 db-upgrade"
    Write-Host "  .\tasks.ps1 seed-core"
    Write-Host "  .\tasks.ps1 seed-dev"
    Write-Host "  .\tasks.ps1 seed-inventory-fixture"
    Write-Host "  .\tasks.ps1 format"
    Write-Host "  .\tasks.ps1 lint"
    Write-Host "  .\tasks.ps1 test"
    Write-Host "  .\tasks.ps1 test-pos"
    Write-Host "  .\tasks.ps1 smoke"
    Write-Host "  .\tasks.ps1 ci-local"
    Write-Host ""
}

switch ($Task) {
    "help" {
        Show-Help
    }

    "install" {
        Invoke-Step "poetry install"
    }

    "precommit" {
        Invoke-Step "poetry run pre-commit install"
    }

    "db-check" {
        Invoke-Step "poetry run python .\devcheck_db.py"
    }

    "db-upgrade" {
        Invoke-Step "poetry run alembic upgrade head"
    }

    "seed-core" {
        Invoke-Step "poetry run python .\seed.py --profile core"
    }

    "seed-dev" {
        Invoke-Step "poetry run python .\seed.py --profile dev"
    }

    "seed-inventory-fixture" {
        Invoke-Step "poetry run python .\seed.py --profile inventory-fixture"
    }

    "format" {
        Invoke-Step "poetry run ruff check src --fix"
        Invoke-Step "poetry run black src"
    }

    "lint" {
        Invoke-Step "poetry run ruff check src"
        Invoke-Step "poetry run black --check src"
    }

    "test" {
        Invoke-Step "poetry run pytest -q"
    }

    "test-pos" {
        Invoke-Step "poetry run pytest -q src/zeromerma_api/tests/test_cash_session_endpoints.py src/zeromerma_api/tests/test_pos_sales_endpoints.py src/zeromerma_api/tests/test_pos_payments_endpoints.py src/zeromerma_api/tests/test_pos_server_side_pricing.py src/zeromerma_api/tests/test_pos_inputs_not_sellable.py src/zeromerma_api/tests/test_concurrency_inventory_balance.py"
    }

    "smoke" {
        Invoke-Step "poetry run pytest -q src/zeromerma_api/tests/test_smoke.py"
    }

    "ci-local" {
        Invoke-Step "poetry run ruff check src"
        Invoke-Step "poetry run black --check src"
        Invoke-Step "poetry run pytest -q"
    }

    default {
        Show-Help
        exit 1
    }
}
