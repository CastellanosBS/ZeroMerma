# apps/backend/scripts/dev-seed.ps1
# Runs the dev seed script using Poetry.
# Robust to being executed from ANY working directory.

# 1) Resolve backend root directory (parent of this scripts/ folder)
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $BackendRoot

# 2) Load DATABASE_URL from .env if not already set
$EnvFile = Join-Path $BackendRoot ".env"
if (-not $env:DATABASE_URL) {
  if (Test-Path $EnvFile) {
    $line = Get-Content $EnvFile | Select-String '^DATABASE_URL=' | Select-Object -First 1
    if ($line) {
      $env:DATABASE_URL = $line.ToString().Split('=',2)[1].Trim()
    }
  } else {
    Write-Warning "No .env found at $EnvFile. Assuming DATABASE_URL is already configured in environment."
  }
}

# 3) Run
poetry run python -m zeromerma_api.scripts.dev_seed
