# scripts/dev-seed.ps1
# Runs the dev seed script using Poetry, reading DATABASE_URL from .env if needed.

Set-Location -Path (Split-Path $PSScriptRoot -Parent)

# Optional: load DATABASE_URL from .env into environment for this session
if (-not $env:DATABASE_URL) {
  $line = Get-Content .\.env | Select-String '^DATABASE_URL=' | Select-Object -First 1
  if ($line) {
    $env:DATABASE_URL = $line.ToString().Split('=',2)[1].Trim()
  }
}

poetry run python -m zeromerma_api.scripts.dev_seed
