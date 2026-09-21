"""Kafa, Defter ve akisin kullandigi adli sabitler: sunucu adresi, model yolu, zaman asimi,
ornekleme, baglam, dosya yollari. Cagiran: yuvalar/kafa.py, yuvalar/defter.py, minik.py."""

from pathlib import Path

KAFA_HOST = "127.0.0.1"
KAFA_PORT = 8080
KAFA_UC = f"http://{KAFA_HOST}:{KAFA_PORT}/v1/chat/completions"

# f0-a'da 25/40 ile secilen model (reports/2026-09-21-f0-turkce-uretim.md).
KAFA_MODEL_YOLU = r"C:\Projelerim\modeller\Qwen3.5-4B-Q4_K_M.gguf"
KAFA_BAGLAM = 8192

# f0'da olculen en yavas tek cevap 10,1 sn (reports/f0-ham-cevaplar/, wall_s); 60 sn genis pay.
KAFA_ZAMAN_ASIMI_SN = 60

# Ornekleme f0 olcumuyle birebir ayni tutulur, sonuc karsilastirilabilir kalsin diye.
KAFA_SICAKLIK = 0.7
KAFA_TOP_P = 0.9
KAFA_MAX_TOKEN = 512

# Spec 4.2: gunluk jsonl defter/ altinda tutulur, .gitignore'da (Minik'in defteri repoya girmez).
DEFTER_KLASORU = Path(__file__).resolve().parent.parent / "defter"
# Baglama giren son kayit sayisi: olculmedi (f2 kapattigi varsayim V14 "ilk sayim"), 10 tur
# (~20 mesaj) hem "dunku konuyu hatirlamaya" yeter hem KAFA_BAGLAM'i (8192) zorlamaz.
DEFTER_SON_N = 10

# oku() DEFTER_SON_N'i bugunku dosya karsilamazsa gun dosyalarinda geriye gider; en cok kac
# gun dosyasi acilacagini sinirlar (180 gun sonra her cagriyi 180 dosya acar hale getirmemek
# icin). Tahmin: bir hafta, "dunku konu" olcutunu rahatca kapsar, gunde birkac kayit varsayimiyla.
DEFTER_GERI_GUN_SINIRI = 7
