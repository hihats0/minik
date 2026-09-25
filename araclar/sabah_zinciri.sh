#!/bin/bash
# Sabah zinciri (25 Eyl 05:25; gece zinciri 02:28'de 91 C ile kesildi): sohbet 500, tohum v0
# egitilip konusturulur, sonra mimari kollar ve merak. Her adim oncekini bekler. Cagiran: ana oturum.
cd /c/Projelerim/minik || exit 1
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
LOG=loglar/gece-zinciri.log
yaz() { echo "$(date '+%F %T') $*" >> "$LOG"; }
izi_var() { [ -f loglar/GPU-SICAK-DURDU ] && yaz "sicak izi var, zincir durdu" && exit 1; }
yaz "sabah zinciri basladi"
python -m cocuk.sohbet_uret --sohbet 500 >> "$LOG" 2>&1; yaz "sohbet 500 bitti: $? ($(wc -l < cocuk/veri/sohbet.jsonl) sohbet)"
izi_var
python -m cocuk.tohum_sohbet >> loglar/tohum-v0.log 2>&1; yaz "tohum v0 bitti: $?, cikti cocuk/agirlik/tohum-v0/konusma.json"
izi_var
python araclar/az_deney_kosu.py hece minik arsifonem; yaz "mimari kollar bitti: $?"
izi_var
python araclar/az_deney_kosu.py merak; yaz "merak bitti: $?"
izi_var
python -m cocuk.sohbet_uret --sohbet 1500 >> "$LOG" 2>&1; yaz "sohbet 1500 bitti: $?"
izi_var
cp -r cocuk/agirlik/tohum-v0 cocuk/agirlik/tohum-v0-500sohbet
python -m cocuk.tohum_sohbet >> loglar/tohum-v0.log 2>&1; yaz "tohum (1500 sohbet) bitti: $?, eski 500 sohbetlik: tohum-v0-500sohbet"
