# Publication boundary for validation evidence. Never upload the raw source tree.
function Invoke-ZeroMermaProtectedValidationProcess {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$ArgumentList,
    [Parameter(Mandatory = $true)][string]$CaptureDirectory
  )
  $ErrorActionPreference = 'Stop'
  $capture = Join-Path ([IO.Path]::GetFullPath($CaptureDirectory)) ([Guid]::NewGuid().ToString('N'))
  $null = New-Item -ItemType Directory -Path $capture
  if ($IsWindows) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $acl = Get-Acl -LiteralPath $capture
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { $null = $acl.RemoveAccessRuleSpecific($rule) }
    $acl.SetOwner($identity.User)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
      $identity.User, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    Set-Acl -LiteralPath $capture -AclObject $acl
  } else {
    [IO.File]::SetUnixFileMode($capture,
      [IO.UnixFileMode]::UserRead -bor [IO.UnixFileMode]::UserWrite -bor [IO.UnixFileMode]::UserExecute)
  }
  $stdoutPath = Join-Path $capture 'stdout.capture'
  $stderrPath = Join-Path $capture 'stderr.capture'
  $stdout = $null
  $stderr = $null
  $process = [Diagnostics.Process]::new()
  $started = $false
  try {
    $stdout = [IO.File]::Open($stdoutPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $stderr = [IO.File]::Open($stderrPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    if (-not $IsWindows) {
      $mode = [IO.UnixFileMode]::UserRead -bor [IO.UnixFileMode]::UserWrite
      [IO.File]::SetUnixFileMode($stdoutPath, $mode)
      [IO.File]::SetUnixFileMode($stderrPath, $mode)
    }
    $process.StartInfo.FileName = $FilePath
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    foreach ($argument in $ArgumentList) { $process.StartInfo.ArgumentList.Add($argument) }
    $started = $process.Start()
    if (-not $started) { throw 'Validation process could not start.' }
    $stdoutCopy = $process.StandardOutput.BaseStream.CopyToAsync($stdout)
    $stderrCopy = $process.StandardError.BaseStream.CopyToAsync($stderr)
    $process.WaitForExit()
    $null = $stdoutCopy.GetAwaiter().GetResult()
    $null = $stderrCopy.GetAwaiter().GetResult()
    $stdout.Dispose(); $stdout = $null
    $stderr.Dispose(); $stderr = $null
    $exitCode = $process.ExitCode
    $content = [IO.File]::ReadAllText($stdoutPath) + [Environment]::NewLine + [IO.File]::ReadAllText($stderrPath)
    $protected = Protect-ZeroMermaValidationText -Text $content
    [Console]::Out.Write($protected)
    return $exitCode
  } finally {
    if ($started -and -not $process.HasExited) { $process.Kill($true); $process.WaitForExit() }
    if ($null -ne $stdout) { $stdout.Dispose() }
    if ($null -ne $stderr) { $stderr.Dispose() }
    $process.Dispose()
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $capture -Force -ErrorAction SilentlyContinue
  }
}

function Protect-ZeroMermaValidationText {
  param([AllowEmptyString()][string]$Text)
  $result = [regex]::Replace($Text,
    '-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z]+ )?PRIVATE KEY-----',
    '[REDACTED PRIVATE KEY]')
  if ($result -match '-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----') {
    throw 'Incomplete private key material cannot be published.'
  }
  $result = [regex]::Replace($result, '(?i)([a-z][a-z0-9+.-]*://)[^\s/@]+(?::[^\s/@]*)?@', '$1[REDACTED]@')
  $result = [regex]::Replace($result, '(?i)(__Host-zm-(?:pos|backoffice)-session=)[^;\s"'']+', '$1[REDACTED]')
  $result = [regex]::Replace($result, '(?im)(\b(?:set-cookie|cookie)\s*:\s*)[^\r\n]+', '$1[REDACTED]')
  $result = [regex]::Replace($result, '(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+', '$1 [REDACTED]')
  $keyedPattern = @'
(?i)(["']?(?:X-CSRF-Token|csrf_token|csrfToken|reset_token|resetToken|current_password|new_password|password|passwd|secret|credential|authorization|cookie)["']?\s*[:=]\s*)(?:"(?:\\.|[^"\\\r\n])*"|'(?:\\.|[^'\\\r\n])*'|[^\s,;}\]]+)
'@
  return [regex]::Replace($result, $keyedPattern.Trim(), '$1"[REDACTED]"')
}

function Protect-ZeroMermaValidationValue {
  param([AllowNull()]$Value)
  if ($Value -is [System.Collections.IDictionary]) {
    $protected = [ordered]@{}
    foreach ($key in $Value.Keys) {
      if ([string]$key -match '(?i)^(?:X-CSRF-Token|csrf_token|csrfToken|reset_token|resetToken|current_password|new_password|password|passwd|secret|credential|authorization|cookie)$') {
        $protected[$key] = '[REDACTED]'
      } else { $protected[$key] = Protect-ZeroMermaValidationValue -Value $Value[$key] }
    }
    return $protected
  }
  if ($Value -is [array]) {
    $items = [System.Collections.Generic.List[object]]::new()
    foreach ($item in $Value) { $items.Add((Protect-ZeroMermaValidationValue -Value $item)) }
    return ,$items.ToArray()
  }
  if ($Value -is [string]) { return Protect-ZeroMermaValidationText -Text $Value }
  return $Value
}

function Protect-ZeroMermaValidationArtifacts {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)][string]$SourceDirectory,
    [Parameter(Mandatory = $true)][string]$DestinationDirectory
  )
  $ErrorActionPreference = 'Stop'
  if (-not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) { return }
  $source = [IO.Path]::GetFullPath($SourceDirectory)
  $destination = [IO.Path]::GetFullPath($DestinationDirectory)
  $comparison = if ($IsWindows) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
  $separator = [IO.Path]::DirectorySeparatorChar
  if ($destination.Equals($source, $comparison) -or
      $destination.StartsWith($source.TrimEnd($separator) + $separator, $comparison) -or
      $source.StartsWith($destination.TrimEnd($separator) + $separator, $comparison)) {
    throw 'Raw and published artifact trees must be distinct non-overlapping directories.'
  }
  foreach ($file in Get-ChildItem -LiteralPath $source -File -Recurse) {
    if ($file.Extension -notin @('.log', '.txt', '.md', '.xml', '.json')) { continue }
    if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
      throw 'Linked artifacts cannot be published.'
    }
    $relative = [IO.Path]::GetRelativePath($source, $file.FullName)
    if ($relative -split '[/\\]' -contains 'tls') { continue }
    $target = Join-Path $destination $relative
    $null = New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force
    if (Test-Path -LiteralPath $target) {
      if (((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'Published artifacts must not replace linked files.'
      }
    }
    $content = [IO.File]::ReadAllText($file.FullName)
    if ($file.Extension -eq '.json') {
      $value = ConvertFrom-Json -InputObject $content -AsHashtable -Depth 100
      $content = ConvertTo-Json -InputObject (Protect-ZeroMermaValidationValue -Value $value) -Depth 100
    } elseif ($file.Extension -eq '.xml') {
      $settings = [Xml.XmlReaderSettings]::new()
      $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
      $settings.XmlResolver = $null
      $reader = [Xml.XmlReader]::Create([IO.StringReader]::new($content), $settings)
      $document = [Xml.XmlDocument]::new()
      $document.PreserveWhitespace = $true
      $document.XmlResolver = $null
      try { $document.Load($reader) } finally { $reader.Dispose() }
      foreach ($node in $document.SelectNodes('//@* | //text()')) {
        $node.Value = Protect-ZeroMermaValidationText -Text $node.Value
      }
      $content = $document.OuterXml
    } else { $content = Protect-ZeroMermaValidationText -Text $content }
    [IO.File]::WriteAllText($target, $content, [Text.UTF8Encoding]::new($false))
  }
}
