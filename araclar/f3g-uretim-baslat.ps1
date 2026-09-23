Set-Location C:\Projelerim\minik
$d='reports\f3g-uretim-durum.txt'
Add-Content $d "$(Get-Date -Format s) f3g uretim basladi"
& .venv\Scripts\python.exe araclar\f3g-kor-uretim.py *> araclar\sunucu-loglari\f3g-uretim.out
$c=$LASTEXITCODE
if($c -eq 0){Add-Content $d "$(Get-Date -Format s) BITTI"}else{Add-Content $d "$(Get-Date -Format s) HATA cikis $c"}
