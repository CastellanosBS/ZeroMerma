[CmdletBinding()]
param(
  [switch]$TestMode,
  [string]$PythonVersionOverride,
  [string]$UvVersionOverride,
  [string]$NodeVersionOverride,
  [string]$CorepackVersionOverride,
  [string]$PnpmVersionOverride
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Throw-ToolchainMismatch {
  param(
    [string]$Tool,
    [string]$Observed,
    [string]$Required,
    [string]$Action
  )

  throw "Toolchain preflight failed: tool=$Tool; observed=$Observed; required=$Required; action=$Action"
}

function Invoke-VersionCommand {
  param(
    [string]$Tool,
    [string]$CommandName,
    [string[]]$Arguments,
    [string]$Required,
    [string]$Action
  )

  $command = Get-Command $CommandName -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if (-not $command) {
    Throw-ToolchainMismatch -Tool $Tool -Observed "missing" -Required $Required -Action $Action
  }

  $output = @(& $command.Source @Arguments 2>&1)
  if ($LASTEXITCODE -ne 0) {
    $observed = if ($output.Count -gt 0) { $output -join " " } else { "command failed" }
    Throw-ToolchainMismatch -Tool $Tool -Observed $observed -Required $Required -Action $Action
  }

  return ($output -join " ").Trim()
}

function Get-SemanticVersion {
  param(
    [string]$Tool,
    [string]$RawVersion,
    [string]$Required,
    [string]$Action
  )

  $match = [regex]::Match($RawVersion, '(?<!\d)(?<version>\d+\.\d+\.\d+)(?!\d)')
  if (-not $match.Success) {
    Throw-ToolchainMismatch -Tool $Tool -Observed $RawVersion -Required $Required -Action $Action
  }

  return [version]$match.Groups['version'].Value
}

function Assert-PolicyFileContains {
  param(
    [string]$Path,
    [string]$Expected,
    [string]$Description
  )

  $content = Get-Content -Raw -LiteralPath $Path
  if (-not $content.Contains($Expected)) {
    throw "Toolchain policy mismatch: $Description. Expected '$Expected' in '$Path'."
  }
}

$overrideValues = @(
  $PythonVersionOverride,
  $UvVersionOverride,
  $NodeVersionOverride,
  $CorepackVersionOverride,
  $PnpmVersionOverride
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

if ($overrideValues.Count -gt 0 -and -not $TestMode) {
  throw "Version overrides are allowed only with -TestMode."
}

Push-Location $Root
try {
  $pythonPolicy = (Get-Content -Raw -LiteralPath ".python-version").Trim()
  if ($pythonPolicy -notmatch '^(?<major>\d+)\.(?<minor>\d+)$') {
    throw "Invalid .python-version policy '$pythonPolicy'; expected major.minor."
  }
  $pythonRequired = "$pythonPolicy.x"
  $pythonMajor = [int]$Matches['major']
  $pythonMinor = [int]$Matches['minor']

  $nodePolicy = (Get-Content -Raw -LiteralPath ".node-version").Trim()
  if ($nodePolicy -notmatch '^(?<major>\d+)$') {
    throw "Invalid .node-version policy '$nodePolicy'; expected a major version."
  }
  $nodeRequired = "$nodePolicy.x"
  $nodeMajor = [int]$Matches['major']

  $pyproject = Get-Content -Raw -LiteralPath "pyproject.toml"
  $uvPolicyMatch = [regex]::Match(
    $pyproject,
    '(?m)^required-version = "==(?<version>\d+\.\d+\.\d+)"$'
  )
  if (-not $uvPolicyMatch.Success) {
    throw "pyproject.toml must declare an exact tool.uv.required-version."
  }
  $uvRequired = $uvPolicyMatch.Groups['version'].Value

  $packageJson = Get-Content -Raw -LiteralPath "package.json" | ConvertFrom-Json
  $packageManager = [string]$packageJson.packageManager
  $pnpmPolicyMatch = [regex]::Match(
    $packageManager,
    '^pnpm@(?<version>\d+\.\d+\.\d+)(?:\+sha512\.[0-9a-f]+)?$'
  )
  if (-not $pnpmPolicyMatch.Success) {
    throw "package.json must declare pnpm with an exact version and optional integrity hash."
  }
  $pnpmRequired = $pnpmPolicyMatch.Groups['version'].Value

  foreach ($projectPath in @("pyproject.toml", "apps/api/pyproject.toml", "apps/worker/pyproject.toml")) {
    Assert-PolicyFileContains `
      -Path $projectPath `
      -Expected "requires-python = `">=$pythonPolicy`"" `
      -Description "Python compatibility must include the canonical runtime"
  }

  Assert-PolicyFileContains `
    -Path ".github/workflows/foundation.yml" `
    -Expected 'python-version-file: ".python-version"' `
    -Description "CI Python policy"
  Assert-PolicyFileContains `
    -Path ".github/workflows/foundation.yml" `
    -Expected "version: `"$uvRequired`"" `
    -Description "CI uv policy"
  Assert-PolicyFileContains `
    -Path ".github/workflows/foundation.yml" `
    -Expected 'node-version-file: ".node-version"' `
    -Description "CI Node policy"
  Assert-PolicyFileContains `
    -Path ".github/workflows/foundation.yml" `
    -Expected "uv sync --all-packages --dev --frozen" `
    -Description "CI frozen Python installation"
  Assert-PolicyFileContains `
    -Path ".github/workflows/foundation.yml" `
    -Expected "corepack pnpm install --frozen-lockfile" `
    -Description "CI frozen Node installation"

  $workflow = Get-Content -Raw -LiteralPath ".github/workflows/foundation.yml"
  if ($workflow.Contains("pnpm/action-setup")) {
    throw "CI must derive pnpm from packageManager through Corepack, not pnpm/action-setup."
  }

  Assert-PolicyFileContains -Path "README.md" -Expected "Python ``$pythonRequired``" -Description "README Python policy"
  Assert-PolicyFileContains -Path "README.md" -Expected "``uv`` ``$uvRequired``" -Description "README uv policy"
  Assert-PolicyFileContains -Path "README.md" -Expected "Node.js ``$nodeRequired``" -Description "README Node policy"
  Assert-PolicyFileContains -Path "README.md" -Expected "``pnpm`` ``$pnpmRequired``" -Description "README pnpm policy"

  $pythonRaw = if ($PythonVersionOverride) {
    $PythonVersionOverride
  }
  else {
    $uvForPython = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue |
      Select-Object -First 1
    if (-not $uvForPython) {
      Throw-ToolchainMismatch `
        -Tool "Python" `
        -Observed "uv missing; canonical Python cannot be resolved" `
        -Required $pythonRequired `
        -Action "Install canonical uv, then run 'uv python install $pythonPolicy'."
    }

    $pythonPathOutput = @(& $uvForPython.Source python find --no-python-downloads $pythonPolicy 2>&1)
    if ($LASTEXITCODE -ne 0 -or $pythonPathOutput.Count -eq 0) {
      $observed = if ($pythonPathOutput.Count -gt 0) { $pythonPathOutput -join " " } else { "missing" }
      Throw-ToolchainMismatch `
        -Tool "Python" `
        -Observed $observed `
        -Required $pythonRequired `
        -Action "Install it with 'uv python install $pythonPolicy'."
    }

    $pythonPath = ([string]$pythonPathOutput[-1]).Trim()
    $pythonOutput = @(& $pythonPath --version 2>&1)
    if ($LASTEXITCODE -ne 0) {
      Throw-ToolchainMismatch `
        -Tool "Python" `
        -Observed ($pythonOutput -join " ") `
        -Required $pythonRequired `
        -Action "Install it with 'uv python install $pythonPolicy'."
    }
    ($pythonOutput -join " ").Trim()
  }
  $pythonObserved = Get-SemanticVersion `
    -Tool "Python" `
    -RawVersion $pythonRaw `
    -Required $pythonRequired `
    -Action "Activate Python $pythonRequired or install it with 'uv python install $pythonPolicy'."
  if ($pythonObserved.Major -ne $pythonMajor -or $pythonObserved.Minor -ne $pythonMinor) {
    Throw-ToolchainMismatch `
      -Tool "Python" `
      -Observed $pythonObserved.ToString() `
      -Required $pythonRequired `
      -Action "Activate Python $pythonRequired or install it with 'uv python install $pythonPolicy'."
  }

  $uvRaw = if ($UvVersionOverride) {
    $UvVersionOverride
  }
  else {
    Invoke-VersionCommand `
      -Tool "uv" `
      -CommandName "uv" `
      -Arguments @("--version") `
      -Required $uvRequired `
      -Action "Install uv $uvRequired using the versioned official installer documented in README.md."
  }
  $uvObserved = Get-SemanticVersion `
    -Tool "uv" `
    -RawVersion $uvRaw `
    -Required $uvRequired `
    -Action "Install uv $uvRequired using the versioned official installer documented in README.md."
  if ($uvObserved.ToString() -ne $uvRequired) {
    Throw-ToolchainMismatch `
      -Tool "uv" `
      -Observed $uvObserved.ToString() `
      -Required $uvRequired `
      -Action "Install uv $uvRequired using the versioned official installer documented in README.md."
  }

  $nodeRaw = if ($NodeVersionOverride) {
    $NodeVersionOverride
  }
  else {
    Invoke-VersionCommand `
      -Tool "Node.js" `
      -CommandName "node" `
      -Arguments @("--version") `
      -Required $nodeRequired `
      -Action "Install and activate Node.js $nodeRequired from an official distribution."
  }
  $nodeObserved = Get-SemanticVersion `
    -Tool "Node.js" `
    -RawVersion $nodeRaw `
    -Required $nodeRequired `
    -Action "Install and activate Node.js $nodeRequired from an official distribution."
  if ($nodeObserved.Major -ne $nodeMajor) {
    Throw-ToolchainMismatch `
      -Tool "Node.js" `
      -Observed $nodeObserved.ToString() `
      -Required $nodeRequired `
      -Action "Install and activate Node.js $nodeRequired from an official distribution."
  }

  $corepackRequired = "available through canonical Node.js $nodeRequired"
  $corepackRaw = if ($CorepackVersionOverride) {
    $CorepackVersionOverride
  }
  else {
    Invoke-VersionCommand `
      -Tool "Corepack" `
      -CommandName "corepack" `
      -Arguments @("--version") `
      -Required $corepackRequired `
      -Action "Use the official Node.js $nodeRequired distribution and run 'corepack enable'."
  }
  $corepackObserved = Get-SemanticVersion `
    -Tool "Corepack" `
    -RawVersion $corepackRaw `
    -Required $corepackRequired `
    -Action "Use the official Node.js $nodeRequired distribution and run 'corepack enable'."

  $pnpmRaw = if ($PnpmVersionOverride) {
    $PnpmVersionOverride
  }
  else {
    Invoke-VersionCommand `
      -Tool "pnpm" `
      -CommandName "corepack" `
      -Arguments @("pnpm", "--version") `
      -Required $pnpmRequired `
      -Action "Run 'corepack enable' and 'corepack prepare pnpm@$pnpmRequired --activate'."
  }
  $pnpmObserved = Get-SemanticVersion `
    -Tool "pnpm" `
    -RawVersion $pnpmRaw `
    -Required $pnpmRequired `
    -Action "Run 'corepack enable' and 'corepack prepare pnpm@$pnpmRequired --activate'."
  if ($pnpmObserved.ToString() -ne $pnpmRequired) {
    Throw-ToolchainMismatch `
      -Tool "pnpm" `
      -Observed $pnpmObserved.ToString() `
      -Required $pnpmRequired `
      -Action "Run 'corepack enable' and 'corepack prepare pnpm@$pnpmRequired --activate'."
  }

  Write-Host "Toolchain preflight passed."
  Write-Host "Python: $pythonObserved (required $pythonRequired)"
  Write-Host "uv: $uvObserved (required $uvRequired)"
  Write-Host "Node.js: $nodeObserved (required $nodeRequired)"
  Write-Host "Corepack: $corepackObserved (required $corepackRequired)"
  Write-Host "pnpm: $pnpmObserved (required $pnpmRequired)"
}
finally {
  Pop-Location
}
