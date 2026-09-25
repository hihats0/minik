"""Kafa'nin bir turda harcadigi gercek is saniyesini (llama-server timings) 0-1 siddete cevirir
(K10, f3-e). Cagiran: minik.py akisi, deneyler/hormon-gunu.py."""

EN_AZ_SIDDET = 0.0
EN_COK_SIDDET = 1.0


def siddet(is_sn, tavan_sn):
    """is_sn'i tavan_sn'e oranlar, 0-1 araligina kirpar. is_sn, llama-server'in kendi olctugu
    prompt_ms + predicted_ms'dir (yuvalar/kafa.py hesaplar). Eskiden burada time.process_time()
    vardi; o Minik'in kendi surecini olcuyordu, is ise harici llama-server surecinde oldugu icin
    gercek akista siddet hep ~0 cikiyordu (reports/2026-09-22-f3e-melatonin-gercek-is.md)."""
    oran = is_sn / tavan_sn
    return max(EN_AZ_SIDDET, min(EN_COK_SIDDET, oran))
