# GPU bekcisi: GPU sicakligini 15 sn'de bir okur, 85 °C'de Minik'in GPU islerini durdurur.
# Cagiran: ana oturum ya da minik-devam rutini, ayri surec olarak (Start-Process pwsh -File ... -WindowStyle Hidden).

$SINIR_DURDUR_C = 93        # Yigit 25 Eyl 22:45: egitim durag 90, bekci onun ustunde son fren (esit olursa yarisir)
$ARALIK_SN = 15
$LOG = "C:\Projelerim\minik\loglar\gpu-bekci.log"
$PROJE = "C:\Projelerim\minik"

function Yaz($metin) {
    Add-Content -Path $LOG -Value ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $metin)
}

function Minik-GpuIsleriniDurdur {
    Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*$PROJE*" -or $_.CommandLine -match 'cocuk\.|f3g-|k23-|llama' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Yaz "durduruldu pid=$($_.ProcessId)" }
}

New-Item -ItemType Directory -Force -Path (Split-Path $LOG) | Out-Null
Yaz "basladi, sinir $SINIR_DURDUR_C C"
while ($true) {
    try {
        $c = [int](nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
        if ($c -ge $SINIR_DURDUR_C) {
            Yaz "SICAK $c C: Minik GPU isleri durduruluyor"
            Minik-GpuIsleriniDurdur
            New-Item -ItemType File -Force -Path "$PROJE\loglar\GPU-SICAK-DURDU" | Out-Null
        }
    } catch {
        Yaz "okuma hatasi: $_"
    }
    Start-Sleep -Seconds $ARALIK_SN
}

