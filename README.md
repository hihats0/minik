# Minik

Büyüyen bir yapay zekâ denemesi: makale ezberleyerek değil, konuşarak öğrenen; gün içinde bir
deftere yazıp gece uykuda pekiştiren; hormon benzeri birkaç sayıyla merakını ve sabrını ayarlayan
küçük bir sistem.

Tasarımın tamamı ve gerekçeleri vault'ta: `🏰 300-Projects/Yazilim/hayal-buyuyen-ai.md`.
Projenin canlı hafızası: `🏰 300-Projects/Yazilim/projeler/minik.md`.

## Yürüyen iskelet

Yedi yuva ilk günden var, her biri en aptal hâliyle. Bir yuvanın arayüzü ancak gerçek bir
uygulaması varken yazılır. Her yuva log tutar, çünkü çalıştığı ölçülmeden iş bitmiş sayılmaz.

| Yuva | İlk hâli | Sonra takılacak |
| --- | --- | --- |
| Kafa | yerel Türkçe LLM, tek arayüz: soru al, metin ver | daha iyi model |
| Kalp | refleks listesi, tek kural | küçük sınıflandırıcılar |
| Çalgıcılar | Python | hesap motoru, Lean |
| Defter | jsonl dosyası | vektör hafıza |
| Uyku | gece çalışan özet script'i | adaptör eğitimi, refleks yazımı |
| Hormonlar | json içinde dört sayı | öğrenilen ayarlar |
| Bekçi | üç ağız kuralı | denetim modeli |

## Durum

Kod öncesi dökümantasyon aşaması. Henüz kod yok, henüz model indirilmedi.

Çıkan belgeler:

- `reports/2026-09-20-kafa-modeli-adaylari.md`: 12 yerel Türkçe LLM adayı, her biri için
  Q4_K_M boyutu, 8 GB VRAM'de güvenli bağlam hesabı (FP16 ve 8 bit KV ayrı), lisans metninden
  okunmuş ticari kullanım ve türev ağırlık izni. Elenenler gerekçesiyle.
- `reports/2026-09-20-arac-yigini.md`: llama.cpp / Ollama / LM Studio kıyası, Windows 11 +
  RTX 4070 Laptop 8 GB için. Seçim: llama.cpp, Python'dan standart kütüphaneyle.
- `notes/malzeme-listesi.md`: indirilecekler tablosu, 13,7 GB zorunlu.
- `notes/mimari-taslak.md`: yedi yuvanın klasör ağacı, giriş noktası sözleşmeleri, ortak log
  biçimi, Defter kayıt biçimi ve altı karar önerisi (Yiğit onayı bekliyor).

Sıradaki adım: üç aday modelin indirilmesi ve f0 ölçümü (token/sn, tepe VRAM, sıcaklık).
