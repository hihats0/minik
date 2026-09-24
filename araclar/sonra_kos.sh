#!/bin/bash
# Gece zinciri "kalan tohumlar bitti" yazinca verilen kollari yurutucuyle kosar (zincir betigi calisirken
# degistirilmesin diye ayri). Cagiran: ana oturum, ayri surec: bash araclar/sonra_kos.sh merak
cd /c/Projelerim/minik || exit 1
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
until grep -q "kalan tohumlar bitti" loglar/gece-zinciri.log; do sleep 60; done
python araclar/az_deney_kosu.py "$@"
echo "$(date '+%F %T') sonra_kos bitti ($*): $?" >> loglar/gece-zinciri.log
