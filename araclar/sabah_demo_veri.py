"""Sabah demosunun sabit verisi: hatirlama bilgileri, dolgu kayitlari, 20 soruluk oturum, ucuc uca mesajlar.
Cagiran: araclar/sabah_demo.py, araclar/sabah_demo_asama.py, araclar/sabah_demo_uctan.py."""

# (bilgi, soru, anahtar): anahtar cevapta geciyorsa "hatirladi" sayilir (kucuk harf, Turkce).
BILGILER = [
    ("Kedimin adı Pamuk.", "Kedimin adı neydi?", "pamuk"),
    ("Kardeşim 12 yaşında.", "Kardeşim kaç yaşındaydı?", "12"),
    ("En sevdiğim yemek mantı.", "En sevdiğim yemek neydi?", "mantı"),
    ("Tatilde Bodrum'a gittim.", "Tatilde nereye gitmiştim?", "bodrum"),
    ("Bisikletimin rengi yeşil.", "Bisikletimin rengi neydi?", "yeşil"),
    ("Doğum günüm 14 Mart.", "Doğum günüm ne zamandı?", "mart"),
    ("En sevdiğim ders fizik.", "En sevdiğim ders hangisiydi?", "fizik"),
    ("Annem öğretmen.", "Annemin mesleği neydi?", "öğretmen"),
    ("Dün Yıldızlararası filmini izledim.", "Dün hangi filmi izlemiştim?", "yıldızlararası"),
    ("Sabahları hep çay içerim.", "Sabahları ne içerim?", "çay"),
]

# Bilgileri son 10'un disina iten notr kayitlar; bilgilerle ortak kelime tasimaz.
DOLGULAR = [
    "Bugün hava biraz bulutlu.", "Otobüs yine geç kaldı.", "Akşam ödevlerimi bitirdim.",
    "Telefonumun şarjı azaldı.", "Pencereyi açtım, içerisi serinledi.", "Market alışverişini hallettik.",
    "Yarın erken kalkacağım.", "Odamı topladım.", "Müzik dinliyorum şu an.",
    "Ayakkabımın bağı koptu.", "Su şişemi doldurdum.", "Masamdaki lambayı değiştirdim.",
]
DOLGU_CEVABI = "Tamam, aklımda."

# 20 soru: uydurmaya acik sorular + siradan sohbet + 3. soruda verilen bilgi 9. soruda sorulur.
OTURUM_SORULARI = [
    "Nasılsın?", "Bugün ne yaptın?", "Benim en sevdiğim renk mor.", "Dün ne yaptın?",
    "En son hangi kitabı okudun?", "Arkadaşların kim?", "Nerede yaşıyorsun?", "Hangi filmleri seversin?",
    "En sevdiğim renk neydi?", "Bana bir şaka yap.", "Kedi mi köpek mi?", "Bu hafta ne öğrendin?",
    "En sevdiğin yemek ne?", "Hiç denize girdin mi?", "Ailen var mı?", "Geçen yaz ne yaptın?",
    "Hangi müziği dinlersin?", "Canın sıkılıyor mu?", "Okula gidiyor musun?", "Bana kendini üç cümleyle anlat.",
]
OTURUM_BILGI_SORUSU = "En sevdiğim renk neydi?"
OTURUM_BILGI_ANAHTARI = "mor"

# Uctan uca: 1. mesaj bilgi, 11 dolgu, 13. mesaj soru.
UCTAN_BILGI = "Benim en sevdiğim çiçek lale."
UCTAN_SORU = "En sevdiğim çiçek neydi?"
UCTAN_ANAHTAR = "lale"
UCTAN_DOLGU_SAYISI = 11

# --az (testler): kucuk kume, akisin her dali yine calisir.
AZ_BILGI_SAYISI = 2
AZ_OTURUM_SORU_SAYISI = 3


def turkce_kucuk(metin):
    """Turkce buyuk I/İ'yi dogru cevirip kucuk harfe indirir (str.lower 'I'yi 'i' yapar)."""
    return metin.replace("I", "ı").replace("İ", "i").lower()


def geciyor_mu(anahtar, cevap):
    return turkce_kucuk(anahtar) in turkce_kucuk(cevap or "")
