[CmdletBinding()]
param(
  [ValidateSet("All", "POS", "Backoffice")][string]$Surface = "All",
  [string]$RunId
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\powershell\ZeroMerma.TestDatabase.ps1")

function Get-FreeLoopbackPort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  try {
    $listener.Start()
    return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
  }
  finally { $listener.Stop() }
}

function Start-IntegrationProcess {
  param([string]$Name, [string]$Executable, [string[]]$Arguments, [string]$Directory)
  $parameters = @{
    FilePath = $Executable
    ArgumentList = $Arguments
    WorkingDirectory = $Directory
    PassThru = $true
    RedirectStandardOutput = (Join-Path $artifactDirectory "$Name.stdout.log")
    RedirectStandardError = (Join-Path $artifactDirectory "$Name.stderr.log")
  }
  if ($env:OS -eq "Windows_NT") { $parameters.WindowStyle = "Hidden" }
  return Start-Process @parameters
}

function Wait-IntegrationServer {
  param([System.Diagnostics.Process]$Process, [string]$Url, [string]$Name)
  for ($attempt = 0; $attempt -lt 120; $attempt++) {
    if ($Process.HasExited) { throw "$Name exited before readiness; see isolated logs" }
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
      if ($response.StatusCode -eq 200) { return }
    }
    catch { }
    Start-Sleep -Milliseconds 500
  }
  throw "$Name did not become ready within the bounded startup window"
}

function Protect-IntegrationArtifacts {
  param([string]$Directory, [string[]]$Secrets)
  foreach ($file in Get-ChildItem -LiteralPath $Directory -Recurse -File) {
    if ($file.Extension -notin @(".log", ".json", ".txt", ".xml", ".md")) { continue }
    $content = [System.IO.File]::ReadAllText($file.FullName)
    foreach ($secretValue in $Secrets) {
      if (-not [string]::IsNullOrWhiteSpace($secretValue)) {
        $content = $content.Replace($secretValue, "[REDACTED]")
      }
    }
    $content = [regex]::Replace($content, '(?i)Bearer\s+[a-z0-9_.=-]+', 'Bearer [REDACTED]')
    $content = [regex]::Replace($content, 'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', '[REDACTED]')
    [System.IO.File]::WriteAllText($file.FullName, $content, [System.Text.UTF8Encoding]::new($false))
  }
}

Invoke-ZeroMermaIsolatedDatabase -RunId $RunId -Action {
  $root = Get-ZeroMermaRepoRoot
  $runIdentity = $env:ZEROMERMA_TEST_RUN_ID
  $artifactDirectory = Join-Path $root ".tmp/validation/web/$runIdentity"
  New-Item -ItemType Directory -Path $artifactDirectory -Force | Out-Null
  $processes = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
  $apiPort = Get-FreeLoopbackPort
  do { $posPort = Get-FreeLoopbackPort } while ($posPort -eq $apiPort)
  do { $backofficePort = Get-FreeLoopbackPort } while ($backofficePort -in @($apiPort, $posPort))
  $apiUrl = "http://127.0.0.1:$apiPort"
  $posUrl = "http://127.0.0.1:$posPort"
  $backofficeUrl = "http://127.0.0.1:$backofficePort"
  $environment = @{
    ZM_WEB_INTEGRATION_ISOLATED = "1"
    ZM_E2E_RUN_ID = $runIdentity
    ZM_E2E_API_URL = $apiUrl
    ZM_E2E_POS_URL = $posUrl
    ZM_E2E_BACKOFFICE_URL = $backofficeUrl
    ZM_E2E_POS_EMAIL = "pos-$runIdentity@example.test"
    ZM_E2E_BACKOFFICE_EMAIL = "reader-$runIdentity@example.test"
    ZM_E2E_PASSWORD = [Guid]::NewGuid().ToString("N")
    ZM_E2E_ARTIFACT_DIR = $artifactDirectory
    ZM_E2E_WORKSTATION_CODE = "POS-01"
    ZEROMERMA_API_ENVIRONMENT = "test"
    ZEROMERMA_API_DATABASE_URL = $env:ZEROMERMA_TEST_DATABASE_URL
    ZEROMERMA_API_AUTH_TOKEN_SECRET = [Guid]::NewGuid().ToString("N")
    ZEROMERMA_API_CORS_ORIGINS = (ConvertTo-Json -Compress @($posUrl, $backofficeUrl))
    ZEROMERMA_API_TRAINING_MODE_ENABLED = "false"
    ZEROMERMA_API_ENABLE_DEV_AUDIT_ENDPOINT = "false"
    ZEROMERMA_WORKER_ENVIRONMENT = "test"
    ZEROMERMA_WORKER_DATABASE_URL = $env:ZEROMERMA_TEST_DATABASE_URL
    VITE_API_BASE_URL = $apiUrl
    VITE_POS_BASE_URL = $posUrl
    VITE_BACKOFFICE_BASE_URL = $backofficeUrl
    VITE_POS_WORKSTATION_CODE = "POS-01"
  }
  $previous = @{}
  try {
    foreach ($key in $environment.Keys) {
      $previous[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
      [Environment]::SetEnvironmentVariable($key, $environment[$key], "Process")
    }
    Invoke-ZeroMermaUv run --frozen python scripts/dev/seed-web-integration.py
    $pythonPath = (& (Resolve-ZeroMermaUvPath) run --frozen python -c "import sys; print(sys.executable)").Trim()
    if ($LASTEXITCODE -ne 0) { throw "Cannot resolve the repository Python runtime" }
    $nodePath = (Get-Command node -CommandType Application | Select-Object -First 1).Source
    $apiProcess = Start-IntegrationProcess -Name "api" -Executable $pythonPath -Directory $root -Arguments @(
      "-m", "uvicorn", "zeromerma_api.main:create_app", "--factory",
      "--app-dir", "apps/api/src", "--host", "127.0.0.1", "--port", "$apiPort"
    )
    $processes.Add($apiProcess)
    Wait-IntegrationServer -Process $apiProcess -Url "$apiUrl/health" -Name "API"
    # Authenticate generated fixtures before any browser can run against an unrelated service.
    $body = @{email = $env:ZM_E2E_POS_EMAIL; password = $env:ZM_E2E_PASSWORD} | ConvertTo-Json
    $null = Invoke-RestMethod -Method Post -Uri "$apiUrl/v1/auth/login" -ContentType "application/json" -Body $body
    Invoke-ZeroMermaUv run --frozen --project apps/worker python -m zeromerma_worker --once

    foreach ($app in @(
      @{Name = "pos"; Folder = "apps/pos-web"; Port = $posPort; Url = $posUrl},
      @{Name = "backoffice"; Folder = "apps/backoffice-web"; Port = $backofficePort; Url = $backofficeUrl}
    )) {
      $webProcess = Start-IntegrationProcess -Name $app.Name -Executable $nodePath -Directory (Join-Path $root $app.Folder) -Arguments @(
        "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "$($app.Port)", "--strictPort"
      )
      $processes.Add($webProcess)
      Wait-IntegrationServer -Process $webProcess -Url $app.Url -Name $app.Name
    }
    if ($Surface -in @("All", "POS")) {
      Invoke-ZeroMermaPnpm --filter @zeromerma/pos-web exec playwright test --config playwright.real.config.ts
    }
    if ($Surface -in @("All", "Backoffice")) {
      Invoke-ZeroMermaPnpm --filter @zeromerma/backoffice-web exec playwright test --config playwright.real.config.ts
    }
    Write-Host "Real browser integration passed: surface=$Surface; run_id=$runIdentity"
  }
  finally {
    $cleanupErrors = [System.Collections.Generic.List[string]]::new()
    try {
      foreach ($process in $processes) {
        try {
          if (-not $process.HasExited) {
            if ($PSVersionTable.PSVersion.Major -ge 7) { $process.Kill($true) }
            elseif ($env:OS -eq "Windows_NT") {
              & taskkill.exe /PID $process.Id /T /F *> $null
            }
            else { $process.Kill() }
            if (-not $process.WaitForExit(10000)) { throw "Process did not stop" }
          }
        }
        catch { $cleanupErrors.Add("Failed to stop integration process $($process.Id)") }
        finally { $process.Dispose() }
      }
      $dbPasswordMatch = [regex]::Match($env:ZEROMERMA_TEST_DATABASE_URL, '://[^:]+:(?<password>[^@]+)@')
      Protect-IntegrationArtifacts -Directory $artifactDirectory -Secrets @(
        $env:ZM_E2E_PASSWORD, $env:ZEROMERMA_API_AUTH_TOKEN_SECRET,
        $env:ZEROMERMA_TEST_DATABASE_URL, $dbPasswordMatch.Groups['password'].Value,
        $env:ZM_E2E_POS_EMAIL, $env:ZM_E2E_BACKOFFICE_EMAIL
      )
    }
    finally {
      foreach ($key in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], "Process")
      }
    }
    if ($cleanupErrors.Count -gt 0) { throw ($cleanupErrors -join "; ") }
  }
}
