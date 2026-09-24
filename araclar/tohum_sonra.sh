#!/bin/bash
# Sohbet uretimi bitince tohum v0'i egitir ve konusturur (ben yokken). Cagiran: ana oturum, ayri surec.
cd /c/Projelerim/minik || exit 1
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
LOG=loglar/gece-zinciri.log
until grep -q "sohbet uretimi bitti" "$LOG"; do sleep 60; done
SAYI=$(wc -l < cocuk/veri/sohbet.jsonl)
if [ "$SAYI" -lt 300 ]; then echo "$(date '+%F %T') tohum atlandi: yalniz $SAYI sohbet" >> "$LOG"; exit 1; fi
python -m cocuk.tohum_sohbet >> loglar/tohum-v0.log 2>&1
echo "$(date '+%F %T') tohum v0 bitti: $? ($SAYI sohbet), cikti cocuk/agirlik/tohum-v0/konusma.json" >> "$LOG"
