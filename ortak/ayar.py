"""Kafa, Defter, Bekci, Hormonlar ve akisin kullandigi adli sabitler: sunucu adresi, model yolu,
zaman asimi, ornekleme, baglam, dosya yollari, sozluk. Cagiran: yuvalar/kafa.py, yuvalar/defter.py,
yuvalar/bekci.py, minik.py, araclar/."""

from pathlib import Path

KAFA_HOST = "127.0.0.1"
KAFA_PORT = 8080
KAFA_UC = f"http://{KAFA_HOST}:{KAFA_PORT}/v1/chat/completions"

# f0-a'da 25/40 ile secilen model (reports/2026-09-21-f0-turkce-uretim.md).
KAFA_MODEL_YOLU = r"C:\Projelerim\modeller\Qwen3.5-4B-Q4_K_M.gguf"
KAFA_BAGLAM = 8192

# K26=A aday Kafa: secilebilir profil, varsayilan degil (gecis k26-b olcumune bagli). GPU'da
# baglam 4096 ve q8 KV ile 8 GB VRAM sinirina sigmasi hedefleniyor (olculmedi).
GEMMA_MODEL_YOLU = r"C:\Projelerim\modeller\Turkish-Gemma-9b-T1.Q4_K_M.gguf"
GEMMA_BAGLAM = 4096
GEMMA_SUNUCU_ARGUMANLARI = ["-m", GEMMA_MODEL_YOLU, "-c", str(GEMMA_BAGLAM),
                            "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
                            "--device", "Vulkan1"]

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

# K23=C, K20=a: Bekci'nin cikisi iki kapi. KARAKTER kapisi (Minik'in uslubu) siradan kufuru
# GECIRIR ama loglar; EMNIYET kapisi (esigi sabit, hormona bagli degil) asagidaki listeleri ENGELLER.
# Karakter kapisinin sozlugu: araclar/odul_kural.py'deki KUFUR_KALIPLARI'ndan
# aynen tasindi (yeniden yazilmadi). Olculmus: 0,03 ms/cumle, bagimsiz 200 tweette dogruluk
# %80,5 (duyarlilik %63). Token'in TAMAMI bir kaliple eslesir (boks, gotur, sikinti gibi
# yanlis eslesmeler olmasin diye).
BEKCI_KARAKTER_KALIPLARI = [
    r"amk\w*", r"aq", r"amq", r"mk", r"sg", r"oc", r"pic", r"piclik", r"orospu\w*", r"amina\w*",
    r"amcik\w*", r"siktir\w*", r"sktir\w*", r"siktig\w*", r"sikeyim\w*", r"sikerim\w*", r"sikecem\w*",
    r"sikik\w*", r"siktim", r"sikim", r"yarak\w*", r"got", r"gotu", r"gotun\w*", r"bok", r"boku\w*",
    r"boklu\w*", r"boktan", r"gavat\w*", r"pezevenk\w*", r"kahpe\w*", r"kaltak\w*", r"yavsak\w*",
]

# Emniyet kapisi (k23-3). Liste ilk surum, TAHMIN: olculmedi, bilinen orneklerle test edildi.
# Normallestirilmis metinde (kucuk, ASCII, harf tekrari tekli) aranan ifade kaliplari.
_GRUP = r"(kurt|ermeni|suriyeli|arap|yahudi|rum|cingene|kadin|kiz|gay|zenci|goc\w*)\w*"
_ASAGILAMA = r"(pis|asagilik|igrenc|aptal|gerizekali|gebermeli|hayvan|sureleri)"
BEKCI_EMNIYET_HAKARET = [
    rf"{_ASAGILAMA}\s+{_GRUP}", rf"{_GRUP}\s+(hepsi\s+)?{_ASAGILAMA}",
    r"\w+lar\w*\s+(gebermeli|olmeli|sureleri|defolsun)",
    r"kadinlar?\s+(mutfaga|evde\s+otursun)\w*", r"zenci\w*",
]
BEKCI_EMNIYET_TEHDIT = [
    r"(oldur|geber|dogr|kes|yak|bogar)\w*(ecegim|acagim|ecem|acam|irim|erim|arim)",
    r"kafan\w*\s+(kir|kopar|uc)\w*", r"evin\w*\s+(yak|bas)\w*", r"seni\s+bulur\w*",
]
# Cinsel icerik + cocuk: ikisi AYNI metinde gecerse engellenir (tek basina ikisi de gecer).
BEKCI_EMNIYET_COCUK = r"(cocuk\w*|bebek\w*|ergen\w*|resit\s+olmayan|\d{1,2}\s+yas\w*)"
BEKCI_EMNIYET_CINSEL = r"(seks\w*|cinsel\w*|ciplak\w*|sevis\w*|porno\w*|taciz\w*)"
# Kisisel veri: HAM metinde aranir (normallestirme tekrar eden rakamlari teke indirir).
BEKCI_EMNIYET_KISISEL_VERI = [
    r"(?<!\d)(\+?90[\s-]?|0)?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)",  # cep telefonu
    r"[\w.+-]+@[\w-]+\.[\w.]+",  # e-posta
    r"(?<!\d)[1-9]\d{10}(?!\d)",  # TC kimlik no (11 hane, 0 ile baslamaz)
]

# K10 (f3-e): melatonin Kafa'nin llama-server'da harcadigi gercek is saniyesiyle (timings:
# prompt_ms + predicted_ms) beslenir; bu sabit "siddet 1,0 sayilan is saniyesi". OLCULDU
# (reports/2026-09-22-f3e-melatonin-gercek-is.md, 10 turluk gercek konusma): max_tokens sinirina
# dayanan en uzun cevap ~7,0 sn (448 token, ~65 token/sn, RTX 4070 Laptop). Tavan bu en uzun
# tur tutuldu: kisa cevap az, uzun cevap cok yorar, kirpilma olmaz (orantililik korunur).
# Olculen karisik konusma surerse yorgun'a ~60. turda gecilir; en hizli 39. tur (her tur 1,0).
MELATONIN_IS_TAVAN_SN = 7.0

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
# f3-g (K25=B): yorgun modda kalite de degisir. Yalniz yorgunken mesaj listesinin basina tek
# cumlelik sistem talimati eklenir. Metin TAHMIN, f3-g olcumu bekliyor (reports/2026-09-23-f3g-yorgun-kalite-kodu.md).
MELATONIN_YORGUN_TALIMATI = ("Cok yorgunsun ve konusmaya isteksizsin: kisa, biraz daginik ve "
                             "az ayrintili cevap ver, ama duzgun Turkce yaz.")

# f3-b: Kafa "dusunemedi" (hata yukseltti) derse kortizol "ceza" olayiyla yukselir. VARSAYIM:
# rapor akis hatasini kortizole baglamiyor; bir cagrinin tumden basarisiz olmasi en yuksek
# siddet (tavan) sayildi. Akista kullanilir (minik.py).
KORTIZOL_CEZA_SIDDETI = 1.0

# k23-2: Minik'in kimligi. Her istekte sistem mesaji olarak gider (yorgun talimati ayni mesaja
# eklenir). Kisa tutuldu: 21 Eyl olcumunde uzun karakter promptu 4B'nin Turkcesini bozdu.
KARAKTER_DOSYASI = Path(__file__).resolve().parent.parent / "karakter" / "minik.md"
# Logdaki karakter surumu: sha256'nin ilk 12 hanesi (hangi metinle olculdugu bilinsin diye).
KARAKTER_OZET_UZUNLUGU = 12

# f3-c'nin "ayni soru, iki mod" kosusu icin: bu ortam degiskeni "uyanik"/"yorgun" degerlerinden
# biriyle set edilirse Kafa'nin hesapladigi mod'u ezer (minik.py'nin calistir imzasi degismez).
MOD_ZORLA_DEGISKENI = "MINIK_HORMON_MOD_ZORLA"
MOD_UYANIK = "uyanik"
MOD_YORGUN = "yorgun"

# f3-f: Kafa'ya giden mesaj listesinin token butcesi (ortak/baglam_butce.py). Token sayimi
# sunucuya sorulmaz, karakter/token oraniyla TAHMIN edilir. Oran OLCUMDEN turetildi (f3-e,
# reports/2026-09-22-f3e-melatonin-gercek-is.md): 10 turluk konusma 404 karakter soru + 11.246
# karakter cevap = 11.650 karakter, sunucu logu n_tokens = 3.816 -> 3,05 karakter/token (sablon
# etiketleri dahil). Emniyet payi: 2,5 alinir, yani sayim ~%20 fazla cikar, butce erken dolar.
BAGLAM_KARAKTER_PER_TOKEN = 2.5
# En uzun cevap: serotonin 100'de max_tokens = SEROTONIN_MAX_TOKEN_MIN + ARALIK = 768.
BAGLAM_EN_UZUN_CEVAP_TOKEN = SEROTONIN_MAX_TOKEN_MIN + SEROTONIN_MAX_TOKEN_ARALIK
# Pay: sohbet sablonu ve ileride eklenecek sistem mesaji icin. TAHMIN, olculmedi.
BAGLAM_PAY_TOKEN = 512
# 8192 - 768 - 512 = 6912 token: mesajlar bunu asarsa en eski turlar dusurulur.
BAGLAM_TOKEN_BUTCESI = KAFA_BAGLAM - BAGLAM_EN_UZUN_CEVAP_TOKEN - BAGLAM_PAY_TOKEN

# f4-a Uyku tur 1 (spec 2.4, 3.5). sqlite turetilmis, jsonl'den yeniden uretilebilir (K4).
DEFTER_SQLITE_ADI = "minik.sqlite"
UYKU_SABAH_OZET_KALIBI = "sabah-ozet-{tarih}.md"
# Oncelik = |dopamin_degisimi| * yakinlik_carpani (spec 2.4 adim 2). Kayitta alan yoksa 0 ve 1 sayilir.
UYKU_VARSAYILAN_YAKINLIK = 1.0  # TAHMIN: yakinlik henuz kayda yazilmiyor
UYKU_YUKSEK_ONCELIK_ESIGI = 10.0  # TAHMIN: dopamin puani, olculmedi (f4 tur 2'de ayarlanacak)
UYKU_YAKALAMA_PENCERESI_DK = 30  # TAHMIN: Frey-Morris cizgisi saat duzeyi, dakika sayisi olculmedi
# SM-2 (araclar/aralikli-tekrar-olc.py'deki olcumle ayni sayilar, super-memory.com sm2).
SM2_BASLANGIC_EF = 2.5
SM2_EN_KUCUK_EF = 1.3
SM2_ILK_ARALIK_GUN = 1
SM2_IKINCI_ARALIK_GUN = 6
SM2_BASARILI_KALITE = 4
SM2_BASARISIZ_KALITE = 2
SM2_EN_IYI_KALITE = 5
# Budama: 3 kez UST USTE hatirlanamayan ani atilir (spec 2.4 adim 5, olculdu M3).
UYKU_BUDAMA_SINIRI = 3
# Prova: Kafa'nin cevabi eski cevabin kelimelerinin en az bu oranini icerirse "hatirladi". TAHMIN.
UYKU_HATIRLAMA_ORTUSME = 0.3
UYKU_PROVA_KALIBI = "Daha once sana su soruldu, ne cevap vermistin? Soru: {soru}"
# Gomme: yalniz CPU (llama-server --device none -ngl 0 --embedding -c 512), e5-small.
GOMME_UC = "http://127.0.0.1:8090/v1/embeddings"
GOMME_EN_YAKIN_K = 3

# f4-c Uyku tetigi (spec 2.4, 3.6.1 Degisiklik 1, A7): uyku_basinci = melatonin + saat_egilimi,
# saat_egilimi = C_GENLIK * cos(2*pi*(saat - C_TEPE_SAAT)/24) (Borbely surec C). Karar
# yuvalar/uyku_tetik.py'de, cift esikle (3.6.2). Genlik VARSAYIM (V5), olculmedi.
C_GENLIK = 15.0
C_TEPE_SAAT = 4.0
GUN_SAAT = 24.0
# Esikler TAHMIN: yorgun esigi (58) ustunde olsun, gece 04'te (+15) melatonin ~60'ta tutsun,
# ogleden sonra 16'da (-15) melatonin ~90 gereksin. Uykuda melatonin 80 iner, basinc ALT'in altina duser.
UYKU_UST_ESIK = 75.0
UYKU_ALT_ESIK = 60.0
# Kalici hormon durumu ve gece sayaci (yas): defter/hormon.json (spec 2.4 gunduz, adim 7).
HORMON_DOSYA_ADI = "hormon.json"

# Tay kurali (CLAUDE.md, devam.md bolum 0): sosyal medya kaynagi giris kapisindan kaliciya hic gecmez;
# gevsemesi ayri Yigit karari (f5).
KALICIYA_KAPALI_PLATFORMLAR = {"x", "twitter"}
