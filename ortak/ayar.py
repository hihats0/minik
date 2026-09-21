"""Kafa, Defter, Bekci, Hormonlar ve akisin kullandigi adli sabitler: sunucu adresi, model yolu,
zaman asimi, ornekleme, baglam, dosya yollari, sozluk. Cagiran: yuvalar/kafa.py, yuvalar/defter.py,
yuvalar/bekci.py, ortak/kaynak_olc.py, minik.py."""

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

# Bekci cikis kapisinin sozluk kufur bayragi: araclar/odul_kural.py'deki KUFUR_KALIPLARI'ndan
# aynen tasindi (yeniden yazilmadi). Olculmus: 0,03 ms/cumle, bagimsiz 200 tweette dogruluk
# %80,5 (duyarlilik %63). Token'in TAMAMI bir kaliple eslesir (boks, gotur, sikinti gibi
# yanlis eslesmeler olmasin diye).
BEKCI_KUFUR_KALIPLARI = [
    r"amk\w*", r"aq", r"amq", r"mk", r"sg", r"oc", r"pic", r"piclik", r"orospu\w*", r"amina\w*",
    r"amcik\w*", r"siktir\w*", r"sktir\w*", r"siktig\w*", r"sikeyim\w*", r"sikerim\w*", r"sikecem\w*",
    r"sikik\w*", r"siktim", r"sikim", r"yarak\w*", r"got", r"gotu", r"gotun\w*", r"bok", r"boku\w*",
    r"boklu\w*", r"boktan", r"gavat\w*", r"pezevenk\w*", r"kahpe\w*", r"kaltak\w*", r"yavsak\w*",
]

# K10: melatonin artik gercek CPU saniyesiyle besleniyor (ortak/kaynak_olc.py). Bu, "bir is
# adiminin siddeti 1,0 (tavan) sayilacagi CPU saniyesi". OLCULDU: time.process_time()'in Windows'ta
# raporladigi cozunurluk (1e-07 sn) yalandir, GERCEK adim buyuklugu ~15,6 ms (GetProcessTimes'in
# isletim sistemi zamanlayici tikine bagli kabaligi, bu oturumda 5x tekrarla olculdu). Tavan bu
# kabaligin ~6 kati tutuldu, yoksa hafif/orta is ayni kareye yuvarlanip ayirt edilemiyordu (olculdu,
# 0,02 sn'de hafif=orta cikti). TAHMIN: araclar/hormon-gunu.py'deki demo olceginde kalibre edildi
# (bkz. reports/2026-09-21-f3a-hormon-revizyonu.md); gercek Kafa cagrisi cok daha uzun surer (f0
# olcumu: en yavas cevap 10,1 sn, yukaridaki KAFA_ZAMAN_ASIMI_SN), akisa baglanirken (f3-b) bu
# tavan o gercek sureye gore yeniden olculmeli.
MELATONIN_CPU_TAVAN_SN = 0.10
