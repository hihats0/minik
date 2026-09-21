"""Bir is bloğunun harcadigi GERCEK CPU saniyesini olcer, 0-1 siddete cevirir (K10: melatonin
artik soyut sayac degil, olculen kaynak tuketimi). Cagiran: araclar/hormon-gunu.py, ileride
minik.py (f3-b, bu kosuda henuz baglanmadi)."""

import time

EN_AZ_SIDDET = 0.0
EN_COK_SIDDET = 1.0


def basla():
    """Bir is blogunun basindaki CPU saatini isaretler. Cagiran isten once bunu, isten sonra
    siddet()'i cagirir."""
    return time.process_time()


def siddet(baslangic, tavan_sn):
    """baslangictan bu yana harcanan CPU saniyesini 0-1 araligina cevirir. tavan_sn'in ustu
    EN_COK_SIDDET'te kirpilir, negatife (saat kaymasi gibi bir durumda) dusmez.

    time.process_time() secildi cunku sadece BU surecin kendi CPU suresini sayar; uyku, ag
    gecikmesi, disk beklemesi saymaz, yani wall-clock'a gore GURULTUSUZ. os.times() ayni veriyi
    verir ama Windows'ta cocuk surec alanlarini (children_user/children_system) sifir dondurur;
    resource modulu (RUSAGE_CHILDREN) Windows'ta hic yok. Tek surecli bir is icin process_time()
    tek sistem cagrisidir (Windows'ta GetProcessTimes), yani en UCUZ olcum de budur."""
    gecen_sn = time.process_time() - baslangic
    oran = gecen_sn / tavan_sn
    return max(EN_AZ_SIDDET, min(EN_COK_SIDDET, oran))
