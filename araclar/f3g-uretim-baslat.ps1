# f3-g uretimini kaldigi yerden devam ettirir (tek parca, en cok 90 dk). Cagiran: ana oturum, arka planda.
# Cikis: 0 tamam, 3 yarim (90 dk doldu, tekrar calistir), 4 sicak (toplam 4 kesme), digeri hata.
Set-Location C:\Projelerim\minik
$d='reports\f3g-uretim-durum.txt'
Add-Content $d "$(Get-Date -Format s) f3g parca basladi"
& python araclar\f3g-kor-uretim.py *>> loglar\f3g-uretim.out
$c=$LASTEXITCODE
$ad=@{0='BITTI';3='YARIM (15 dk sogu, tekrar calistir)';4='SICAK (4 kesme)'}[$c]
if(-not $ad){$ad="HATA cikis $c"}
Add-Content $d "$(Get-Date -Format s) $ad"
exit $c
