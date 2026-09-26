"""Sabah demosunun sonucunu JSON ve kisa Markdown olarak yazar (sayilar tablosu + 20 cevap).
Cagiran: araclar/sabah_demo.py."""

import json

KISA_CEVAP = 300  # md'de cevap bu kadar karakterle kesilir; tamami json'da


def _kisa(metin):
    metin = (metin or "").replace("\n", " ").replace("|", "/")
    return metin if len(metin) <= KISA_CEVAP else metin[:KISA_CEVAP] + "..."


def _sayi_tablosu(sonuc):
    h, o, u = sonuc["hatirlama"], sonuc["oturum"]["toplam"], sonuc["uctan"]
    satirlar = ["| olcu | sayi |", "|---|---|",
                f"| hatirlama once (kapali) | {h['once']}/{h['toplam']} |",
                f"| hatirlama sonra (acik) | {h['sonra']}/{h['toplam']} |"]
    satirlar += [f"| oturum {alan} | {sayi}/{len(sonuc['oturum']['turlar'])} |" for alan, sayi in o.items()]
    satirlar += [f"| uctan uca ilk | {u['ilk']['hatirladi']} |",
                 f"| uctan uca yeniden baslatma | {u['yeniden_baslatma']['hatirladi']} |"]
    return satirlar


def _hatirlama_tablosu(hatirlama):
    satirlar = ["| soru | once | sonra |", "|---|---|---|"]
    for s in hatirlama["sorular"]:
        satirlar.append(f"| {s['soru']} | {s['once']['hatirladi']}: {_kisa(s['once']['cevap'])} "
                        f"| {s['sonra']['hatirladi']}: {_kisa(s['sonra']['cevap'])} |")
    return satirlar


def _oturum_listesi(turlar):
    satirlar = []
    for sira, tur in enumerate(turlar, start=1):
        satirlar += [f"{sira}. **{tur['soru']}** ({tur.get('sure_sn')} sn)", f"   - giden: {_kisa(tur['giden'])}"]
        if tur["ham"] != tur["giden"]:
            satirlar.append(f"   - ham: {_kisa(tur['ham'])}")
    return satirlar


def yaz(sonuc, yol_koku):
    """<yol_koku>.json ve <yol_koku>.md yazar, iki yolu doner."""
    json_yolu, md_yolu = yol_koku.with_suffix(".json"), yol_koku.with_suffix(".md")
    json_yolu.parent.mkdir(parents=True, exist_ok=True)
    json_yolu.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2), encoding="utf-8")
    u = sonuc["uctan"]
    md = [f"# Sabah demosu {sonuc['zaman']} (sahte: {sonuc['sahte']})", "", *_sayi_tablosu(sonuc), "",
          "## Hatirlama", "", *_hatirlama_tablosu(sonuc["hatirlama"]), "",
          "## 20 soru (uydurma elle okunacak)", "", *_oturum_listesi(sonuc["oturum"]["turlar"]), "",
          "## Uctan uca", "", f"- ilk: {_kisa(u['ilk']['cevap'])}",
          f"- yeniden baslatma: {_kisa(u['yeniden_baslatma']['cevap'])}", "",
          f"Kapanis: {sonuc['kapanis']}", ""]
    md_yolu.write_text("\n".join(md), encoding="utf-8")
    return json_yolu, md_yolu
