# Karar masasini disaridan acilir hale getirir: yerel sunucuyu ve Cloudflare quick tunnel'i
# baslatir, telefondan girilecek adresi ekrana basar. Cagiran: Yigit, elle.
# Not: quick tunnel adresi her acilista DEGISIR (kalici adres Cloudflare hesabi + alan adi ister).

$kok = Split-Path -Parent $PSScriptRoot
$log = Join-Path $env:TEMP "minik-tunnel.log"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
    Write-Host "cloudflared yok. Kurmak icin: winget install Cloudflare.cloudflared" -ForegroundColor Red
    exit 1
}

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Sunucu baslatiliyor..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList (Join-Path $kok "araclar\karar-sunucu.py") -WorkingDirectory $kok -WindowStyle Hidden

Write-Host "Tunnel aciliyor..." -ForegroundColor Cyan
Start-Process -FilePath $cloudflared -ArgumentList 'tunnel','--url','http://127.0.0.1:8765' -RedirectStandardError $log -RedirectStandardOutput "$log.out" -WindowStyle Hidden

$adres = $null
$bitis = (Get-Date).AddSeconds(45)
while (-not $adres -and (Get-Date) -lt $bitis) {
    Start-Sleep -Seconds 2
    $satir = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($satir) { $adres = $satir.Matches[0].Value }
}

if ($adres) {
    Write-Host "`nTelefondan gir:" -ForegroundColor Green
    Write-Host "  $adres`n" -ForegroundColor Green
    Write-Host "Cevaplar: notes\karar-cevaplari.json"
    Write-Host "Kapatmak icin: Get-Process cloudflared,python | Stop-Process"
} else {
    Write-Host "Tunnel adresi alinamadi. Log: $log" -ForegroundColor Red
}
