#Requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\powershell\ZeroMerma.Tools.ps1')
. (Join-Path $PSScriptRoot '..\powershell\ZeroMerma.Tls.ps1')
$repoRoot = Get-ZeroMermaRepoRoot
& (Join-Path $PSScriptRoot 'check-toolchain.ps1')
foreach ($port in @(8000, 5173, 5174)) {
  $probe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
  try { $probe.Start() }
  catch { throw "Local port $port is already in use. Stop that service before starting ZeroMerma." }
  finally { $probe.Stop() }
}
$runDirectory = Join-Path $repoRoot ('.tmp/validation/local/' + [Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $runDirectory -Force
$tls = New-ZeroMermaEphemeralTlsCertificate -OutputDirectory (Join-Path $runDirectory 'tls')
$apiUrl = 'https://127.0.0.1:8000'
$posUrl = 'https://127.0.0.1:5173'
$backofficeUrl = 'https://127.0.0.1:5174'
$environment = @{
  ZEROMERMA_API_ENVIRONMENT = 'local'
  ZEROMERMA_WORKER_ENVIRONMENT = 'local'
  ZEROMERMA_API_CORS_ORIGINS = (ConvertTo-Json -Compress @($posUrl, $backofficeUrl))
  ZEROMERMA_API_SESSION_POS_ORIGINS = (ConvertTo-Json -Compress -AsArray $posUrl)
  ZEROMERMA_API_SESSION_BACKOFFICE_ORIGINS = (ConvertTo-Json -Compress -AsArray $backofficeUrl)
  ZEROMERMA_API_ENABLE_API_DOCS = 'false'
  ZM_LOCAL_HTTPS = '1'
  ZM_LOCAL_TLS_CERT_FILE = $tls.CertificatePath
  ZM_LOCAL_TLS_KEY_FILE = $tls.PrivateKeyPath
  VITE_API_BASE_URL = $apiUrl
  VITE_POS_BASE_URL = $posUrl
  VITE_BACKOFFICE_BASE_URL = $backofficeUrl
}
$previousEnvironment = @{}
$startedProcesses = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-LocalService {
  param([string]$Name, [string]$Executable, [string]$Directory, [string[]]$Arguments)
  $windowOptions = @{}
  if ($IsWindows) { $windowOptions.WindowStyle = 'Hidden' }
  $process = Start-Process @windowOptions -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $Directory `
    -PassThru -RedirectStandardOutput (Join-Path $runDirectory "$Name.stdout.log") `
    -RedirectStandardError (Join-Path $runDirectory "$Name.stderr.log")
  $startedProcesses.Add($process)
  return @{ name = $Name; pid = $process.Id }
}
Push-Location $repoRoot
try {
  foreach ($key in $environment.Keys) {
    $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
    [Environment]::SetEnvironmentVariable($key, $environment[$key], 'Process')
  }
  Invoke-ZeroMermaUv sync --all-packages --dev --frozen
  Invoke-ZeroMermaUv run --frozen python -c 'from sqlalchemy.engine import make_url; from zeromerma_api.core.config import get_settings as api; from zeromerma_worker.core.config import get_settings as worker; urls=[make_url(str(settings().database_url)) for settings in (api, worker)]; assert all(u.host in ("localhost", "127.0.0.1", "::1") and u.database == "zeromerma" and (u.port or 5432) == 5432 for u in urls), "start-local requires API and worker on the canonical loopback development database"'
  Invoke-ZeroMermaPnpm install --frozen-lockfile
  Invoke-ZeroMermaPnpm contracts:generate
  Start-ZeroMermaPostgres
  Wait-ZeroMermaPostgres
  Invoke-ZeroMermaApiMigrations
  Invoke-ZeroMermaApiSeedLocalData
  $pythonPath = (& (Resolve-ZeroMermaUvPath) run --frozen python -c 'import sys; print(sys.executable)').Trim()
  if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the Python runtime.' }
  $nodePath = (Get-Command node -CommandType Application | Select-Object -First 1).Source
  $services = @(
    (Start-LocalService -Name 'api' -Executable $pythonPath -Directory $repoRoot -Arguments @(
      '-m', 'uvicorn', 'zeromerma_api.main:create_app', '--factory', '--app-dir', 'apps/api/src',
      '--host', '127.0.0.1', '--port', '8000', '--no-proxy-headers',
      '--ssl-certfile', ('"' + $tls.CertificatePath + '"'), '--ssl-keyfile', ('"' + $tls.PrivateKeyPath + '"'))),
    (Start-LocalService -Name 'worker' -Executable $pythonPath -Directory $repoRoot -Arguments @('-m', 'zeromerma_worker')),
    (Start-LocalService -Name 'pos' -Executable $nodePath -Directory (Join-Path $repoRoot 'apps/pos-web') -Arguments @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort')),
    (Start-LocalService -Name 'backoffice' -Executable $nodePath -Directory (Join-Path $repoRoot 'apps/backoffice-web') -Arguments @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5174', '--strictPort'))
  )
  $services | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDirectory 'processes.json') -Encoding utf8
  foreach ($url in @("$apiUrl/health", $posUrl, $backofficeUrl)) {
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
      if (@($startedProcesses | Where-Object HasExited).Count -gt 0) {
        throw "A local service exited. Inspect the logs in $runDirectory."
      }
      try {
        $null = Invoke-WebRequest -Uri $url -SkipCertificateCheck -TimeoutSec 2
        $ready = $true
        break
      } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw "Local HTTPS service did not become ready: $url" }
  }
  Write-Host "Local services started. Logs and process IDs: $runDirectory"
  Write-Host "API: $apiUrl/health"
  Write-Host "POS: $posUrl"
  Write-Host "Backoffice: $backofficeUrl"
  Write-Host 'The disposable certificate expires in 24 hours. No OS trust was installed.'
  Write-Host 'Accept this development certificate for each URL in the browser before signing in.'
} catch {
  foreach ($process in $startedProcesses) {
    if (-not $process.HasExited) { $process.Kill($true); $process.WaitForExit(5000) | Out-Null }
  }
  throw
} finally {
  foreach ($key in $previousEnvironment.Keys) {
    [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], 'Process')
  }
  Pop-Location
}
