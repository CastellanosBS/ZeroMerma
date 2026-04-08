$script:ZeroMermaRepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script:ZeroMermaComposeFile = Join-Path $script:ZeroMermaRepoRoot "infra\docker\docker-compose.yml"

function Get-ZeroMermaRepoRoot {
  return $script:ZeroMermaRepoRoot
}

function Get-ZeroMermaComposeFile {
  return $script:ZeroMermaComposeFile
}

function Format-ZeroMermaCommandPath {
  param([string]$Path)

  return "'$($Path.Replace("'", "''"))'"
}

function Resolve-ZeroMermaUvPath {
  $command = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($command) {
    return $command.Source
  }

  $repoLocalUv = Join-Path $script:ZeroMermaRepoRoot ".venv\Scripts\uv.exe"
  if (Test-Path -LiteralPath $repoLocalUv -PathType Leaf) {
    return $repoLocalUv
  }

  throw @"
uv CLI was not found.

Install uv globally on Windows, then open a new PowerShell terminal:
  winget install --id Astral-sh.UV

Alternative official installer:
  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"

Do not run ZeroMerma scripts from a random external virtual environment. These scripts resolve the uv CLI directly and manage the repository .venv themselves.
"@
}

function Resolve-ZeroMermaPnpmCommand {
  $pnpm = Get-Command pnpm -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($pnpm) {
    return [pscustomobject]@{
      Path = $pnpm.Source
      Arguments = @()
    }
  }

  $corepack = Get-Command corepack -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($corepack) {
    return [pscustomobject]@{
      Path = $corepack.Source
      Arguments = @("pnpm")
    }
  }

  throw "pnpm was not found. Install Node.js 22 with Corepack enabled, then run: corepack prepare pnpm@9.15.4 --activate"
}

function Resolve-ZeroMermaDockerPath {
  $docker = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($docker) {
    return $docker.Source
  }

  throw "Docker was not found. Install Docker Desktop for Windows and ensure the docker CLI is available in PowerShell."
}

function Get-ZeroMermaUvCommandExpression {
  $uvPath = Resolve-ZeroMermaUvPath
  return "& $(Format-ZeroMermaCommandPath $uvPath)"
}

function Get-ZeroMermaPnpmCommandExpression {
  $pnpm = Resolve-ZeroMermaPnpmCommand
  $parts = @("&", (Format-ZeroMermaCommandPath $pnpm.Path))
  $parts += $pnpm.Arguments
  return $parts -join " "
}

function Invoke-ZeroMermaUv {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

  $uvPath = Resolve-ZeroMermaUvPath
  & $uvPath @Arguments

  if ($LASTEXITCODE -ne 0) {
    throw "uv failed with exit code $LASTEXITCODE. Command: uv $($Arguments -join ' ')"
  }
}

function Invoke-ZeroMermaPnpm {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

  $pnpm = Resolve-ZeroMermaPnpmCommand
  $invokeArguments = @()
  $invokeArguments += $pnpm.Arguments
  $invokeArguments += $Arguments
  & $pnpm.Path @invokeArguments

  if ($LASTEXITCODE -ne 0) {
    throw "pnpm failed with exit code $LASTEXITCODE. Command: pnpm $($Arguments -join ' ')"
  }
}

function Invoke-ZeroMermaDockerCompose {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

  $dockerPath = Resolve-ZeroMermaDockerPath
  $invokeArguments = @("compose", "-f", $script:ZeroMermaComposeFile)
  $invokeArguments += $Arguments
  & $dockerPath @invokeArguments

  if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed with exit code $LASTEXITCODE. Command: docker compose -f $script:ZeroMermaComposeFile $($Arguments -join ' ')"
  }
}

function Invoke-ZeroMermaApiMigrations {
  Invoke-ZeroMermaUv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
}

function Invoke-ZeroMermaApiSeedLocalData {
  Invoke-ZeroMermaUv run --project apps/api python scripts/bootstrap/seed-local-data.py
}

function Start-ZeroMermaPostgres {
  Write-Host "Starting PostgreSQL..."
  $arguments = @("up", "-d", "postgres")
  Invoke-ZeroMermaDockerCompose @arguments
}

function Wait-ZeroMermaPostgres {
  param(
    [int]$Attempts = 30,
    [int]$DelaySeconds = 2
  )

  $dockerPath = Resolve-ZeroMermaDockerPath

  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    & $dockerPath compose -f $script:ZeroMermaComposeFile exec -T postgres pg_isready -U zeromerma -d zeromerma *> $null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "PostgreSQL is ready."
      return
    }

    Start-Sleep -Seconds $DelaySeconds
  }

  throw "PostgreSQL did not become ready after $Attempts attempts. Check Docker Desktop and inspect logs with: docker compose -f infra\docker\docker-compose.yml logs postgres"
}
