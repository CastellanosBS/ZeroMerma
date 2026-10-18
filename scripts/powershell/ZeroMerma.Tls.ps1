# Disposable TLS material for isolated browser validation. No OS trust is installed.
function New-ZeroMermaEphemeralTlsCertificate {
  [CmdletBinding()]
  param([Parameter(Mandatory = $true)][string]$OutputDirectory)

  $ErrorActionPreference = 'Stop'
  $repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
  $validationRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot '.tmp\validation'))
  $destination = [IO.Path]::GetFullPath($OutputDirectory)
  $prefix = $validationRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
  if (-not $destination.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Ephemeral TLS material must be inside the workspace validation directory.'
  }
  $null = New-Item -ItemType Directory -Path $destination -Force
  $certPath = Join-Path $destination 'localhost.crt.pem'
  $keyPath = Join-Path $destination 'localhost.key.pem'
  if ((Test-Path -LiteralPath $certPath) -or (Test-Path -LiteralPath $keyPath)) {
    throw 'Ephemeral TLS output must not overwrite existing material.'
  }

  $rsa = [Security.Cryptography.RSA]::Create(3072)
  $certificate = $null
  $keyStream = $null
  try {
    $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
      'CN=localhost', $rsa, [Security.Cryptography.HashAlgorithmName]::SHA256,
      [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $san = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $san.AddDnsName('localhost')
    $san.AddIpAddress([Net.IPAddress]::Parse('127.0.0.1'))
    $san.AddIpAddress([Net.IPAddress]::Parse('::1'))
    $request.CertificateExtensions.Add($san.Build())
    $request.CertificateExtensions.Add(
      [Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true))
    $certificate = $request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5), [DateTimeOffset]::UtcNow.AddHours(24))
    $keyStream = [IO.File]::Open($keyPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    if ($IsWindows) {
      $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
      $acl = Get-Acl -LiteralPath $keyPath
      $acl.SetAccessRuleProtection($true, $false)
      foreach ($rule in @($acl.Access)) { $null = $acl.RemoveAccessRuleSpecific($rule) }
      $acl.SetOwner($identity.User)
      $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity.User, 'FullControl', 'Allow'))
      Set-Acl -LiteralPath $keyPath -AclObject $acl
    } else {
      [IO.File]::SetUnixFileMode($keyPath, [IO.UnixFileMode]::UserRead -bor [IO.UnixFileMode]::UserWrite)
    }
    $keyBytes = [Text.Encoding]::UTF8.GetBytes($rsa.ExportPkcs8PrivateKeyPem())
    $keyStream.Write($keyBytes, 0, $keyBytes.Length)
    $keyStream.Flush($true)
    $keyStream.Dispose()
    $keyStream = $null
    [IO.File]::WriteAllText($certPath, $certificate.ExportCertificatePem(), [Text.UTF8Encoding]::new($false))
  } catch {
    if ($null -ne $keyStream) { $keyStream.Dispose(); $keyStream = $null }
    Remove-Item -LiteralPath $keyPath, $certPath -Force -ErrorAction SilentlyContinue
    throw
  } finally {
    if ($null -ne $keyStream) { $keyStream.Dispose() }
    if ($null -ne $certificate) { $certificate.Dispose() }
    $rsa.Dispose()
  }
  [pscustomobject]@{ CertificatePath = $certPath; PrivateKeyPath = $keyPath }
}
