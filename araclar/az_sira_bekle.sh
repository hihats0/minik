#!/bin/bash
# Az-veri deneyi: calisan yurutucu "hepsi bitti" ya da "durdu" yazinca sonraki kollari baslatir.
# Cagiran: ana oturum, arka planda `bash araclar/az_sira_bekle.sh arsifonem minik`.
LOG=loglar/az-deney-kosu.log
BASLANGIC=$(wc -l < "$LOG")
until tail -n +"$((BASLANGIC + 1))" "$LOG" | grep -qE "hepsi bitti|durdu|basarisiz|tavani"; do sleep 30; done
if tail -n +"$((BASLANGIC + 1))" "$LOG" | grep -qE "durdu|basarisiz"; then
    echo "onceki yurutucu hatayla durdu, sonraki kollar baslatilmadi"; tail -3 "$LOG"; exit 1
fi
# Ayri Windows sureci: bu betik bitince olmesin (Start-Process).
KOLLAR=$(printf "'%s'," "$@"); KOLLAR=${KOLLAR%,}
powershell -NoProfile -Command "\$env:PYTHONUNBUFFERED='1'; \$env:PYTHONIOENCODING='utf-8'; Start-Process -FilePath python -ArgumentList @('araclar\az_deney_kosu.py',$KOLLAR) -WorkingDirectory 'C:\Projelerim\minik' -WindowStyle Hidden"
sleep 20; tail -2 "$LOG"
