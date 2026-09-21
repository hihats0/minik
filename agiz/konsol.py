"""Ilk agiz: konsoldan okur, konsola yazar. Cagiran: minik.py akisi."""


def dinle():
    """Konsoldan bir satir soru okur, bastaki/sondaki bosluklari siler."""
    return input("Sen: ").strip()


def soyle(metin, dis_id):
    """Cevabi konsola yazar. dis_id konsolda kullanilmiyor (tek kullanici var); imza sozlesme
    geregi sabit, baska bir agiz (ornegin dosya) ayni imzayla kim'e yazacagini bilir."""
    print(f"Minik: {metin}")
