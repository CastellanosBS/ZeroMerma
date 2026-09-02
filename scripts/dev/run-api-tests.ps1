[CmdletBinding()]
param(
  [string[]]$TestTarget = @("apps/api/tests"),
  [string]$RunId
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.Tools.ps1")

$repoRoot = Get-ZeroMermaRepoRoot
$toolchainScript = Join-Path $PSScriptRoot "check-toolchain.ps1"
$runIdPattern = '^[a-z0-9][a-z0-9_]{7,39}$'

if ([string]::IsNullOrWhiteSpace($RunId)) {
  $RunId = [Guid]::NewGuid().ToString("N")
}
if ($RunId -notmatch $runIdPattern) {
  throw "RunId must contain 8-40 lowercase alphanumeric/underscore characters."
}
if ($TestTarget.Count -eq 0) {
  throw "At least one pytest target is required."
}

$databaseName = "zeromerma_test_$RunId"
$databaseUser = "zeromerma_test_runner"
$databasePassword = [Guid]::NewGuid().ToString("N")
$applicationName = $databaseName
$confirmation = "ALLOW_ZEROMERMA_DESTRUCTIVE_TESTS:$RunId"
$containerName = "zeromerma-test-postgres-$RunId"
$testEnvironmentNames = @(
  "ZEROMERMA_TEST_ENVIRONMENT",
  "ZEROMERMA_TEST_DATABASE_URL",
  "ZEROMERMA_TEST_RUN_ID",
  "ZEROMERMA_TEST_DESTRUCTIVE_CONFIRMATION"
)
$previousEnvironment = @{}
$containerCreated = $false

foreach ($name in $testEnvironmentNames) {
  $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

Push-Location $repoRoot
try {
  $powerShellPath = (Get-Process -Id $PID).Path
  & $powerShellPath -NoProfile -File $toolchainScript
  if ($LASTEXITCODE -ne 0) {
    throw "Canonical toolchain preflight failed."
  }
  $null = Resolve-ZeroMermaDockerPath

  $containerId = & docker run `
    --detach `
    --rm `
    --name $containerName `
    --label "com.zeromerma.test-run-id=$RunId" `
    --publish "127.0.0.1::5432" `
    --mount "type=tmpfs,destination=/var/lib/postgresql/data,tmpfs-size=536870912" `
    --env "POSTGRES_DB=$databaseName" `
    --env "POSTGRES_USER=$databaseUser" `
    --env "POSTGRES_PASSWORD=$databasePassword" `
    postgres:16-alpine
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($containerId)) {
    throw "Failed to create the isolated PostgreSQL test container."
  }
  $containerCreated = $true

  $mounts = (& docker inspect --format '{{json .Mounts}}' $containerName | ConvertFrom-Json)
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect the isolated PostgreSQL test container."
  }
  $persistentMounts = @($mounts | Where-Object { $_.Type -eq "volume" })
  $testDataMount = @(
    $mounts | Where-Object {
      $_.Type -eq "tmpfs" -and $_.Destination -eq "/var/lib/postgresql/data"
    }
  )
  if ($persistentMounts.Count -ne 0 -or $testDataMount.Count -ne 1) {
    throw "Ephemeral PostgreSQL must use only tmpfs for its data directory."
  }

  $ready = $false
  for ($attempt = 1; $attempt -le 60; $attempt++) {
    & docker exec $containerName pg_isready -U $databaseUser -d $databaseName *> $null
    if ($LASTEXITCODE -eq 0) {
      $ready = $true
      break
    }
    Start-Sleep -Milliseconds 500
  }
  if (-not $ready) {
    throw "Ephemeral PostgreSQL did not become ready within 30 seconds."
  }

  $portOutput = (& docker port $containerName 5432/tcp | Select-Object -First 1).Trim()
  if ($LASTEXITCODE -ne 0 -or $portOutput -notmatch ':(?<port>\d+)$') {
    throw "Could not resolve the loopback port for ephemeral PostgreSQL."
  }
  $hostPort = [int]$Matches['port']
  $databaseUrl = (
    "postgresql+psycopg://${databaseUser}:${databasePassword}" +
    "@127.0.0.1:${hostPort}/${databaseName}?application_name=${applicationName}"
  )

  [Environment]::SetEnvironmentVariable("ZEROMERMA_TEST_ENVIRONMENT", "test", "Process")
  [Environment]::SetEnvironmentVariable("ZEROMERMA_TEST_DATABASE_URL", $databaseUrl, "Process")
  [Environment]::SetEnvironmentVariable("ZEROMERMA_TEST_RUN_ID", $RunId, "Process")
  [Environment]::SetEnvironmentVariable(
    "ZEROMERMA_TEST_DESTRUCTIVE_CONFIRMATION",
    $confirmation,
    "Process"
  )

  Write-Host (
    "Ephemeral test database ready: run_id=$RunId; host=127.0.0.1; " +
    "port=$hostPort; database=$databaseName; user=$databaseUser"
  )
  Invoke-ZeroMermaUv run --frozen pytest @TestTarget
  Write-Host "Ephemeral API database tests passed: run_id=$RunId; database=$databaseName"
}
finally {
  foreach ($name in $testEnvironmentNames) {
    [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], "Process")
  }

  if ($containerCreated) {
    $existingContainer = & docker ps -a --quiet --filter "name=^/${containerName}$"
    if (-not [string]::IsNullOrWhiteSpace($existingContainer)) {
      & docker rm --force $containerName *> $null
    }
  }
  Pop-Location
}
