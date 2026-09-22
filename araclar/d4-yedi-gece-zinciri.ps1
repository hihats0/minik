# D4 yedi gece zinciri: ders uretimi, transformer 7 gece, kor tamamlama puani (SSM Yigit istegiyle yok).
# Cagiran: yonetici oturum, Start-Process ile ayri surec. Bitince cocuk/agirlik/d4-gece-durum.txt icine BITTI yazar.
$ErrorActionPreference = "Continue"
Set-Location "C:\Projelerim\minik"
$durum = "cocuk\agirlik\d4-gece-durum.txt"
"$(Get-Date -Format s) ders_uret basladi" | Out-File $durum -Encoding utf8
python -m cocuk.ders_uret *> cocuk\agirlik\d4-ders-uret.out
"$(Get-Date -Format s) ders_uret bitti (cikis $LASTEXITCODE), yedi_gece transformer basladi" | Out-File $durum -Append -Encoding utf8
python -m cocuk.yedi_gece --ad d4-transformer --tur transformer *> cocuk\agirlik\d4-yedi-gece-transformer.out
"$(Get-Date -Format s) yedi_gece bitti (cikis $LASTEXITCODE), tamamlama_puanla basladi" | Out-File $durum -Append -Encoding utf8
python -m cocuk.tamamlama_puanla --adlar d4-transformer *> cocuk\agirlik\d4-tamamlama.out
"$(Get-Date -Format s) tamamlama_puanla bitti (cikis $LASTEXITCODE)" | Out-File $durum -Append -Encoding utf8
"BITTI" | Out-File $durum -Append -Encoding utf8
