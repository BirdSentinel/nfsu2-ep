$ErrorActionPreference = 'Stop'
$decalRoot = Join-Path $PSScriptRoot 'decals'
if (!(Test-Path -LiteralPath $decalRoot)) { New-Item -ItemType Directory -Path $decalRoot | Out-Null }
$items = @()
$total = 0L
foreach ($file in Get-ChildItem -LiteralPath $decalRoot -Recurse -File | Sort-Object FullName) {
    if ($file.Extension.ToLowerInvariant() -notin @('.png', '.jpg', '.jpeg')) { continue }
    if ($file.Length -gt 32MB -or $items.Count -ge 128 -or ($total + $file.Length) -gt 64MB) {
        Write-Warning "Skipped oversized library entry: $($file.Name)"
        continue
    }
    $mime = if ($file.Extension.ToLowerInvariant() -eq '.png') { 'image/png' } else { 'image/jpeg' }
    $data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($file.FullName))
    $items += @{name=$file.Name; url="data:$mime;base64,$data"}
    $total += $file.Length
}
$json = ConvertTo-Json -InputObject @($items) -Compress -Depth 4
$destination = Join-Path $PSScriptRoot 'library.js'
[IO.File]::WriteAllText($destination, "window.DECAL_LIBRARY=$json;", [Text.UTF8Encoding]::new($false))
Write-Output "Decal library: $($items.Count) images."
