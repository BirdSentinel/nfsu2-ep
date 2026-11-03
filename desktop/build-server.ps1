param([string]$Binary = '', [string]$Output = '', [string]$Python = '')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
if (!$Binary) { $Binary = Join-Path $repoRoot 'web/server-rs/target/x86_64-pc-windows-gnu/ci/egyuttparkolas-server.exe' }
if (!$Output) { $Output = Join-Path $repoRoot 'out/portable/Egyuttparkolas-Server' }
if (!(Test-Path -LiteralPath $Binary -PathType Leaf)) { throw "Build the native Rust server first. Missing: $Binary" }
New-Item -ItemType Directory -Path $Output -Force | Out-Null
Copy-Item -LiteralPath $Binary -Destination (Join-Path $Output 'Egyuttparkolas-Server.exe') -Force
if ($Python) {
  & $Python (Join-Path $PSScriptRoot 'set-icon.py') (Join-Path $Output 'Egyuttparkolas-Server.exe') (Join-Path $PSScriptRoot 'icon.png')
  if ($LASTEXITCODE -ne 0) { throw 'Could not embed the server icon.' }
}
if (!(Test-Path -LiteralPath (Join-Path $Output 'server.json'))) {
  [IO.File]::WriteAllText((Join-Path $Output 'server.json'), '{"bind":"0.0.0.0","port":8080,"max_players":49}', [Text.UTF8Encoding]::new($false))
}
Copy-Item -LiteralPath (Join-Path $repoRoot 'docs/web/ONLINE-SERVER.md') -Destination (Join-Path $Output 'READ-ME.md') -Force
Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE') -Destination (Join-Path $Output 'LICENSE.txt') -Force
Write-Output "Portable server: $Output"
