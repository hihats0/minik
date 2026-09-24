#!/bin/bash
# Gece zinciri (25 Eyl): AdamW yurutucusu bitince sirayla sohbet dumani, hece ve minik tohum 1,
# uzun sohbet uretimi, kalan tohumlar. Her adim oncekini bekler. Cagiran: ana oturum, ayri surec.
cd /c/Projelerim/minik || exit 1
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
LOG=loglar/gece-zinciri.log
yaz() { echo "$(date '+%F %T') $*" >> "$LOG"; }
BAS=$(wc -l < loglar/az-deney-kosu.log)
until tail -n +"$((BAS + 1))" loglar/az-deney-kosu.log | grep -qE "hepsi bitti|durdu|basarisiz|tavani"; do sleep 30; done
yaz "adamw bitti"
python -m cocuk.sohbet_uret --sohbet 20 >> "$LOG" 2>&1; yaz "sohbet dumani bitti: $?"
python araclar/az_deney_kosu.py hece@1 minik@1; yaz "hece ve minik tohum 1 bitti: $?"
python -m cocuk.sohbet_uret --sohbet 3000 >> "$LOG" 2>&1; yaz "sohbet uretimi bitti: $?"
python araclar/az_deney_kosu.py hece minik arsifonem; yaz "kalan tohumlar bitti: $?"
