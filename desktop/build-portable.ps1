param(
    [string]$Data = 'C:\Games\Need for Speed Underground 2',
    [string]$Module = (Join-Path $PSScriptRoot '../out/web'),
    [string]$Frontend = (Join-Path $PSScriptRoot '../web/dist'),
    [string]$ElectronVersion = '45.2.1',
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot
$output = Join-Path $repo 'out/portable/Egyuttparkolas'
$cache = Join-Path $repo 'out/electron-cache'
foreach ($file in @((Join-Path $Data 'SPEED2.EXE'), (Join-Path $Module 'nfsu2.wasm'), (Join-Path $Module 'nfsu2.json'), (Join-Path $Frontend 'index.html'), (Join-Path $Frontend 'main.js'))) {
    if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing build input: $file. See docs/web/PORTABLE.md." }
}
if ((Get-FileHash -LiteralPath (Join-Path $Data 'SPEED2.EXE') -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'f9dd86c054878ce6276beb07c1fd61874f7a1e4bf1f241b084c65b73e24168a7') { throw 'The game executable does not match the required v1.2 North America build.' }
if (Test-Path -LiteralPath $output) { throw "Output already exists: $output. Move it elsewhere before rebuilding (it may contain your saves)." }
if ($ElectronVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid Electron version.' }
New-Item -ItemType Directory -Force -Path $cache | Out-Null
$name = "electron-v$ElectronVersion-win32-x64.zip"
$zip = Join-Path $cache $name
$base = "https://github.com/electron/electron/releases/download/v$ElectronVersion"
if (!(Test-Path -LiteralPath $zip)) { Invoke-WebRequest "$base/$name" -OutFile $zip }
$sums = (Invoke-WebRequest "$base/SHASUMS256.txt").Content
if ($sums -is [byte[]]) { $sums = [Text.Encoding]::UTF8.GetString($sums) }
$line = ($sums -split "`n" | Where-Object { $_.TrimEnd().EndsWith(" *$name") -or $_.TrimEnd().EndsWith("  $name") } | Select-Object -First 1)
if (!$line -or (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne ($line -split '\s+')[0]) { throw 'Electron archive checksum failed. Remove the cached ZIP and retry.' }
Expand-Archive -LiteralPath $zip -DestinationPath $output
Rename-Item -LiteralPath (Join-Path $output 'electron.exe') -NewName 'Egyuttparkolas.exe'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'icon.png') -Destination (Join-Path $output 'icon.png')
& $Python (Join-Path $PSScriptRoot 'set-icon.py') (Join-Path $output 'Egyuttparkolas.exe') (Join-Path $output 'icon.png')
if ($LASTEXITCODE -ne 0) { throw 'Icon embedding failed. The build requires Python with Pillow.' }
$appDir = Join-Path $output 'resources/app'
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'package.json'), (Join-Path $PSScriptRoot 'main.cjs'), (Join-Path $PSScriptRoot 'server.cjs'), (Join-Path $PSScriptRoot 'vinyls.cjs') -Destination $appDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'studio-preload.cjs'), (Join-Path $PSScriptRoot 'studio-library.cjs') -Destination $appDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'launcher-preload.cjs'), (Join-Path $PSScriptRoot 'studio-export.cjs') -Destination $appDir
Copy-Item -LiteralPath $Frontend -Destination (Join-Path $output 'web') -Recurse
Copy-Item -LiteralPath (Join-Path $Module 'nfsu2.wasm') -Destination (Join-Path $output 'web/game.wasm')
Copy-Item -LiteralPath (Join-Path $Module 'nfsu2.json') -Destination (Join-Path $output 'web/game.json')
$game = Join-Path $output 'game'
New-Item -ItemType Directory -Path $game | Out-Null
$entries = 'speed2.exe server.dll server.cfg cars credits frontend global langpacks languages memcard movies nis pfdata sdata sound speech subtitles texpacks tracks' -split ' '
foreach ($item in Get-ChildItem -LiteralPath $Data) {
    if ($entries -contains $item.Name.ToLowerInvariant()) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Game input must not contain links: $($item.FullName)" }
        Copy-Item -LiteralPath $item.FullName -Destination $game -Recurse
    }
}
Copy-Item -LiteralPath (Join-Path $repo 'licenses') -Destination (Join-Path $output 'licenses') -Recurse
Copy-Item -LiteralPath (Join-Path $repo 'LICENSE') -Destination (Join-Path $output 'licenses/project-MIT.txt')
Copy-Item -LiteralPath (Join-Path $repo 'docs/web/PORTABLE.md') -Destination (Join-Path $output 'READ-ME.md')
Copy-Item -LiteralPath (Join-Path $repo 'docs/web/PNG-VINYLS.md') -Destination (Join-Path $output 'PNG-VINYLS.md')
$studio = Join-Path $repo 'out/vinyl-studio'
if (Test-Path -LiteralPath (Join-Path $studio 'models.js')) {
    Copy-Item -LiteralPath $studio -Destination (Join-Path $output 'VinylStudio') -Recurse
    [IO.File]::WriteAllText((Join-Path $output 'Open-Vinyl-Studio.cmd'), "@echo off`r`ncall `"%~dp0VinylStudio\Open-Vinyl-Studio.cmd`"`r`n", [Text.Encoding]::ASCII)
}
Write-Host "Ready: $output\Egyuttparkolas.exe"
Write-Host 'Copy the ENTIRE Egyuttparkolas folder to the USB drive.'
