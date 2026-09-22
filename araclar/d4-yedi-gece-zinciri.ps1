# D4 yedi gece zinciri: ders uretimi, transformer 7 gece, kor tamamlama puani (SSM Yigit istegiyle yok).
# Cagiran: yonetici oturum, Start-Process ile ayri surec. Bitince cocuk/agirlik/d4-gece-durum.txt icine
# BITTI yazar; bir adim sifirdan farkli cikisla biterse HATA yazar ve sonraki adimlar baslamaz.
$ErrorActionPreference = "Continue"
Set-Location "C:\Projelerim\minik"
$durum = "cocuk\agirlik\d4-gece-durum.txt"

function Adim($ad, $komut, $cikti) {
    "$(Get-Date -Format s) $ad basladi" | Out-File $durum -Append -Encoding utf8
    & python @komut *> $cikti
    $kod = $LASTEXITCODE
    "$(Get-Date -Format s) $ad bitti (cikis $kod)" | Out-File $durum -Append -Encoding utf8
    if ($kod -ne 0) {
        "HATA: $ad cikis $kod, zincir durdu (log: $cikti)" | Out-File $durum -Append -Encoding utf8
        exit $kod
    }
}

"$(Get-Date -Format s) zincir basladi" | Out-File $durum -Encoding utf8
Adim "ders_uret" @("-m", "cocuk.ders_uret") "cocuk\agirlik\d4-ders-uret.out"
Adim "yedi_gece transformer" @("-m", "cocuk.yedi_gece", "--ad", "d4-transformer", "--tur", "transformer") "cocuk\agirlik\d4-yedi-gece-transformer.out"
Adim "tamamlama_puanla" @("-m", "cocuk.tamamlama_puanla", "--adlar", "d4-transformer") "cocuk\agirlik\d4-tamamlama.out"
"BITTI" | Out-File $durum -Append -Encoding utf8
