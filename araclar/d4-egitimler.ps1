# D4 on egitim zinciri: once transformer, sonra SSM, sirayla (tek GPU). Cagiran: elle, arka planda.
# Bitince cocuk/agirlik/d4-egitim-durum.txt icine BITTI yazar.
$ErrorActionPreference = "Continue"
Set-Location "C:\Projelerim\minik"
$durum = "cocuk\agirlik\d4-egitim-durum.txt"
"$(Get-Date -Format s) transformer basladi" | Out-File $durum -Encoding utf8
python -m cocuk.egit --tur transformer --ad d4-transformer --token-milyon 200 --saat 3 --batch 16 --birikim 2 *> cocuk\agirlik\d4-transformer.out
"$(Get-Date -Format s) transformer bitti (cikis $LASTEXITCODE), ssm basladi" | Out-File $durum -Append -Encoding utf8
python -m cocuk.egit --tur ssm --ad d4-ssm --token-milyon 200 --saat 5 --batch 8 --birikim 4 *> cocuk\agirlik\d4-ssm.out
"$(Get-Date -Format s) ssm bitti (cikis $LASTEXITCODE)" | Out-File $durum -Append -Encoding utf8
"BITTI" | Out-File $durum -Append -Encoding utf8
