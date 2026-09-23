"""Ikinci agiz (f8-a, spec 2.6): girdi dosyasindan satir satir soru okur, cevaplari cikti dosyasina yazar.
Konsol agziyla ayni sozlesme (dinle, soyle). Cagiran: agiz/secim.py (minik.py --agiz dosya), testler."""

from pathlib import Path

PLATFORM = "dosya"
VARSAYILAN_GIRDI = Path("dosya-agzi") / "girdi.txt"
VARSAYILAN_CIKTI = Path("dosya-agzi") / "cikti.txt"
CIKIS_KELIMESI = "cik"  # minik.CIKIS_KELIMESI ile ayni; dosya bitince akis bu kelimeyle durur


class DosyaAgzi:
    """Girdi dosyasini acilista okur (bos satirlar atlanir), her dinle() bir satir verir."""

    def __init__(self, girdi=VARSAYILAN_GIRDI, cikti=VARSAYILAN_CIKTI):
        metin = Path(girdi).read_text(encoding="utf-8")
        self._sorular = [s.strip() for s in metin.splitlines() if s.strip()]
        self._cikti = Path(cikti)
        self._cikti.parent.mkdir(parents=True, exist_ok=True)

    def dinle(self):
        """Siradaki soruyu verir; dosya bitince cikis kelimesi doner (akis durur)."""
        if not self._sorular:
            return CIKIS_KELIMESI
        return self._sorular.pop(0)

    def soyle(self, metin, dis_id):
        """Cevabi cikti dosyasinin sonuna bir satir olarak ekler; dis_id konsoldaki gibi kullanilmaz."""
        with self._cikti.open("a", encoding="utf-8") as f:
            f.write(f"Minik: {metin}\n")
