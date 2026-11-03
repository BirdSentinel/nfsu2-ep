param(
    [string]$Data = 'C:\Games\Need for Speed Underground 2',
    [string]$Distribution = 'Ubuntu',
    [string]$LinuxRepo = '/root/nfsu2-ep',
    [ValidateRange(1024, 65535)][int]$Port = 8080,
    [ValidateRange(1, 6)][int]$Players = 2
)
$ErrorActionPreference = 'Stop'
try {
    if (!(Test-Path -LiteralPath (Join-Path $Data 'SPEED2.EXE'))) {
        throw "SPEED2.EXE was not found in $Data. Pass -Data with your game folder."
    }
    $url = "http://localhost:$Port/?localPlayers=$Players"
    function Test-GameServer {
        try {
            # WSL forwards this listener over IPv4. Avoid localhost's IPv6
            # fallback delay in Windows PowerShell's older HTTP client.
            $manifest = Invoke-RestMethod "http://127.0.0.1:$Port/game.json" -TimeoutSec 5
            return ($manifest.pages -gt 0 -and $manifest.guestEnd -gt 0)
        } catch { return $false }
    }
    if (!(Test-GameServer)) {
        $linuxData = & wsl.exe -d $Distribution -u root --exec wslpath -a $Data
        if ($LASTEXITCODE -ne 0) { throw 'Ubuntu is not ready. Complete WSL setup first.' }
        $linuxData = ($linuxData -join '').Trim()
        if ($Distribution -notmatch '^[A-Za-z0-9_.-]+$' -or $LinuxRepo -notmatch '^/[A-Za-z0-9_./-]+$' -or $linuxData.Contains('"')) {
            throw 'Use a distribution name and Linux build path without spaces or quotes; the game folder may contain spaces.'
        }
        $logDir = Join-Path $PSScriptRoot '../out/windows'
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        $arguments = "-d $Distribution -u root --cd $LinuxRepo --exec bash web/start.sh --no-build --data `"$linuxData`" --http-port $Port"
        $server = Start-Process wsl.exe -ArgumentList $arguments -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $logDir 'server.log') `
            -RedirectStandardError (Join-Path $logDir 'server-error.log')
        $ready = $false
        for ($attempt = 0; $attempt -lt 120; $attempt++) {
            if (Test-GameServer) { $ready = $true; break }
            if ($server.HasExited) { break }
            Start-Sleep -Milliseconds 500
        }
        if (!$ready) { throw "The game server did not start. See $logDir\server-error.log and server.log." }
    }
    $chrome = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($chrome) { Start-Process $chrome -ArgumentList $url }
    else { Start-Process $url }
    Write-Host "Game ready at $url - press Play in your browser."
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
