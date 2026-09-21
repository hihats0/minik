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

# f3-b, kademe 1 (reports/2026-09-20-hormon-mimarisi.md bolum 1): hormon -> Kafa'nin ornekleme
# ayarlarina donusumu (donusum yuvalar/kafa.py'de, K6: akis karar vermez). YON rapordan:
# noradrenalin->sicaklik+top_p (kesif rastgeleligi), serotonin->max_token (sabir), kortizol->
# repeat_penalty (gerginlik tekrara dusurur). ARALIKLARIN SAYISI rapor vermiyor, sadece yon:
# VARSAYIM, olculmedi. Dinlenme degerlerinde (noradrenalin 20, serotonin 50, kortizol 10) bu
# formuller f0'in olctugu KAFA_SICAKLIK/KAFA_TOP_P/KAFA_MAX_TOKEN'a yakin ama BIREBIR AYNI DEGIL;
# hormon verisi yokken (testler, hormonsuz cagrilar) yine de f0'in olctugu sabit ayni kalir.
NORADRENALIN_SICAKLIK_MIN = 0.5
NORADRENALIN_SICAKLIK_ARALIK = 0.7  # sicaklik 0,5 - 1,2 arasinda gezer
NORADRENALIN_TOP_P_MIN = 0.80
NORADRENALIN_TOP_P_ARALIK = 0.18  # top_p 0,80 - 0,98 arasinda gezer
SEROTONIN_MAX_TOKEN_MIN = 128
SEROTONIN_MAX_TOKEN_ARALIK = 640  # max_token 128 - 768 arasinda gezer
KORTIZOL_REPEAT_PENALTY_MIN = 1.0
KORTIZOL_REPEAT_PENALTY_ARALIK = 0.3  # repeat_penalty 1,0 - 1,3 arasinda gezer

# Melatonin tek basina AC/KAPA (surekli degil) bir karar surer: "yorgun mu". Spec 3.6.2 (M1)
# kurali: bu turden bir karar ALT_ESIK/UST_ESIK adli iki sabitle (cift esik/Schmitt tetikleyici)
# yapilir. 42/58 OLCULDU (araclar/histerezis-olc.py, 8 tohum x 4 olay yogunlugu x 300 adim, gercek
# hormonlar.py ile): tek esige gore 1,5-2,9 kat az mod titremesi. Minik'in gercek olay
# yogunlugunda YENIDEN OLCULMEDI (V6, spec'in kendi notu); bu kosuda ayni olculen sayilar kullanildi.
ALT_ESIK = 42.0
UST_ESIK = 58.0
# Yorgun modda n_predict ve sicaklik asagi cekilir (rapor: "yorgun Minik kisa ve donuk konusur").
# Carpanlarin SAYISI VARSAYIM, rapor sadece yon veriyor.
MELATONIN_YORGUN_SICAKLIK_CARPANI = 0.7
MELATONIN_YORGUN_MAX_TOKEN_CARPANI = 0.5

# f3-b: Kafa "dusunemedi" (hata yukseltti) derse kortizol "ceza" olayiyla yukselir. VARSAYIM:
# rapor akis hatasini kortizole baglamiyor; bir cagrinin tumden basarisiz olmasi en yuksek
# siddet (tavan) sayildi. Akista kullanilir (minik.py).
KORTIZOL_CEZA_SIDDETI = 1.0

# f3-c'nin "ayni soru, iki mod" kosusu icin: bu ortam degiskeni "uyanik"/"yorgun" degerlerinden
# biriyle set edilirse Kafa'nin hesapladigi mod'u ezer (minik.py'nin calistir imzasi degismez).
MOD_ZORLA_DEGISKENI = "MINIK_HORMON_MOD_ZORLA"
MOD_UYANIK = "uyanik"
MOD_YORGUN = "yorgun"
