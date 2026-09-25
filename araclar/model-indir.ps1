# k23-1 aday modellerin GGUF Q4_K_M dosyalarini C:\Projelerim\modeller altina indirir.
# Yonetici elle baslatir; hesap ve gerekce: reports/2026-09-23-k23-adaylar.md
$ErrorActionPreference = "Stop"
$HEDEF_KLASOR = "C:\Projelerim\modeller"
$DOSYA_SINIRI_GB = 11
$TOPLAM_SINIRI_GB = 20
$BOS_DISK_ALTSINIR_GB = 25   # indirme sonrasi C: en az bu kadar bos kalsin

# Boyutlar Hub'dan okundu (2026-09-23), GB = 1e9 bayt
$ADAYLAR = @(
    @{ Depo = "mradermacher/Trendyol-LLM-8B-T1-i1-GGUF";        Dosya = "Trendyol-LLM-8B-T1.i1-Q4_K_M.gguf";          GB = 5.03 },
    @{ Depo = "ytu-ce-cosmos/Turkish-Gemma-9b-T1-GGUF";          Dosya = "Turkish-Gemma-9b-T1.Q4_K_M.gguf";            GB = 5.76 },
    @{ Depo = "bartowski/mlabonne_Qwen3-8B-abliterated-GGUF";   Dosya = "mlabonne_Qwen3-8B-abliterated-Q4_K_M.gguf";  GB = 5.03 }
)

$toplam = ($ADAYLAR | Measure-Object -Property GB -Sum).Sum
if ($toplam -gt $TOPLAM_SINIRI_GB) { throw "Toplam $toplam GB, sinir $TOPLAM_SINIRI_GB GB" }
foreach ($a in $ADAYLAR) {
    if ($a.GB -gt $DOSYA_SINIRI_GB) { throw "$($a.Dosya) $($a.GB) GB, sinir $DOSYA_SINIRI_GB GB" }
}
$bosGB = (Get-PSDrive C).Free / 1e9
if (($bosGB - $toplam) -lt $BOS_DISK_ALTSINIR_GB) { throw "Bos disk $([math]::Round($bosGB,1)) GB, indirme sonrasi $BOS_DISK_ALTSINIR_GB GB altina iner" }

New-Item -ItemType Directory -Force $HEDEF_KLASOR | Out-Null
foreach ($a in $ADAYLAR) {
    $yol = Join-Path $HEDEF_KLASOR $a.Dosya
    if (Test-Path $yol) { Write-Host "Zaten var: $yol"; continue }
    Write-Host "Indiriliyor: $($a.Depo) / $($a.Dosya) ($($a.GB) GB)"
    hf download $a.Depo $a.Dosya --local-dir $HEDEF_KLASOR
    if ($LASTEXITCODE -ne 0) { throw "hf download basarisiz: $($a.Dosya)" }
}
Write-Host "Bitti. Toplam $toplam GB."
