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

Kurulum aşaması. Henüz kod yok.
