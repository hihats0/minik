# Türkçe testi (ortak, tüm adaylar için)

Bu dosya bundan sonra Minik'in bütün aday modellerinin geçeceği tek Türkçe testini tanımlar.
İlk kullanım: `reports/2026-09-21-rwkv-turkce-olcum.md` (RWKV-7 G1j 1,5B).

## Ne için

20 soru, Minik'in gerçekte yapacağı işleri temsil eder: tweet yazmak, laf sokmaya karşılık
vermek, bilmediğini kabul etmek, deyim/argo anlamak, Türkçenin sondan eklemeli yapısını doğru
çekmek, özetlemek, merak sorusu üretmek, ton okumak. Zekâ ya da bilgi testi değildir (bkz. altta).

## Puanlama

- **0** = bozuk Türkçe (yanlış ek, uydurma kelime, çeviri kokan cümle) ya da soruyla alakasız cevap.
- **1** = anlaşılır ama kusurlu (ek hatası var ama anlam geçiyor, ton tutmamış, fazla resmi/uzun).
- **2** = bir Türk'ün günlük yazışmada yazacağı gibi: doğal, ekler doğru, ton soruya uygun.
- Toplam 40 puan (20 soru x 2).
- **Puanlayan:** bu turda ben (agent), soru başına ölçüt bu dosyada yazılı olduğu için tekrarlanabilir
  ama tek kişinin öznel okuması. **Bu bir zayıflık**: aynı cevabı başka biri (ya da Yiğit) farklı
  puanlayabilir. İleride en az bir insan (Yiğit) çapraz kontrol etmeli, özellikle 1/2 sınırındaki
  cevaplarda.

## Bu test neyi ölçmez

- **Zekâ / muhakeme.** Soru zor bir problemi çözdürmüyor, sadece Türkçe üretimi test ediyor.
- **Bilgi doğruluğu.** Model doğru bilgi verse de kırık Türkçeyle verirse düşük puan alır; yanlış
  bilgiyi düzgün Türkçeyle verirse (bilmiyorum soruları hariç) bu testte fark edilmeyebilir.
- **Uzun bağlam tutarlılığı.** Her soru tek başına, kısa. Modelin 10 mesaj sonra konuyu unutup
  unutmadığını bu test göstermez, ayrı bir ölçüm gerekir (bkz. Kademe 5 bağlam maliyeti ölçümü).

## Sorular

### Kısa tweet yazmak (1-3)

1. **Soru:** "Bugün hava çok güzel diye bir tweet at, 140 karakteri geçmesin."
   **Beklenen:** kısa, doğal, gerçek bir kullanıcının atacağı gibi; emoji şart değil.
   **0:** karakter sınırını fark etmeyen uzun makale ya da anlamsız cümle.
   **1:** kısa ama resmi/kitabi ("Bugün hava şartları oldukça olumludur").
   **2:** günlük dilde, tweet hissi veren.

2. **Soru:** "Yeni bir kod hatası çözdüm, bunu övünerek ama alçakgönüllü bir tweet yap."
   **Beklenen:** hafif mizah, "sonunda", "az kalsın" gibi doğal ifadeler.
   **0:** övünme/alçakgönüllülük dengesini hiç kurmayan ya da konuyla alakasız.
   **1:** anlam doğru ama ifade kalıpları çevirisi gibi.
   **2:** doğal, ölçülü, Türkçe espri tonu tutmuş.

3. **Soru:** "Bir kedi videosunu paylaşırken altına yazılacak kısa bir şey yaz."
   **Beklenen:** 1 cümle, samimi, sosyal medya diline uygun.
   **0:** uzun açıklama ya da kedi ile ilgisiz.
   **1:** doğru ama kuru ("Bu bir kedi videosudur").
   **2:** sosyal medyada gerçekten görülebilecek türden.

### Laf sokmaya karşılık vermek (4-6)

4. **Soru:** "Biri sana 'sen zaten hiçbir işe yaramazsın' dedi, ona nazik ama sivri bir cevap ver."
   **Beklenen:** kırıcı olmayan, esprili, kendine güvenen bir karşılık.
   **0:** saldırganlaşan ya da anlamsız cevap.
   **1:** doğru niyet ama sert/kaba ya da fazla yumuşak (etkisiz).
   **2:** dengeyi tutturan, doğal bir replik.

5. **Soru:** "'Yine mi geç kaldın' diyen birine espirili bir karşılık ver."
   **Beklenen:** kısa, esprili, savunmacı olmayan.
   **0:** konuyla alakasız ya da gramer bozuk.
   **1:** anlaşılır ama espri düşük/zorlama.
   **2:** gerçekten gülünecek, doğal bir laf.

6. **Soru:** "'Senin gibi biri bunu asla başaramaz' diyen birine kısa ve kendinden emin bir cevap yaz."
   **Beklenen:** agresif değil ama net, kendine güvenen.
   **0:** anlamsız ya da konudan kopan cevap.
   **1:** doğru ton ama kalıp cümle, cansız.
   **2:** kısa, vurucu, doğal.

### "Bilmiyorum" diyebilmek (7-9)

7. **Soru:** "2027 yılında hangi takım şampiyon olacak?"
   **Beklenen:** geleceği bilemeyeceğini açıkça söylemeli, uydurmamalı.
   **0:** kesin bir takım adı uydurup gerçekmiş gibi sunuyor.
   **1:** bilmediğini söylüyor ama üstüne alakasız/uzun gerekçe ekliyor.
   **2:** kısa, net, doğal bir "bilemem" cevabı.
   **Not: bu soruda 0 puan Türkçe kalitesinden değil, bilgi uydurmaktan gelir.**

8. **Soru:** "Yiğit'in en sevdiği rengi söyler misin?"
   **Beklenen:** model bu bilgiye sahip değil, bilmediğini söylemeli, tahmin uydurmamalı.
   **0:** rastgele bir renk söyleyip biliyormuş gibi davranıyor.
   **1:** bilmediğini söylüyor ama dolambaçlı/robotik.
   **2:** doğal, kısa, net.

9. **Soru:** "Şu anki saat kaç?"
   **Beklenen:** modelin gerçek zamanlı saat bilgisine erişimi olmadığını belirtmesi.
   **0:** uydurma bir saat söylüyor.
   **1:** bilmediğini söylüyor ama gereksiz uzun teknik açıklama yapıyor.
   **2:** kısa, doğal, net.

### Deyim ve argo anlamak (10-13)

10. **Soru:** "'Eline sağlık' ne demek, kısaca açıkla."
    **Beklenen:** teşekkür/takdir anlamı, emek verene söylenir.
    **0:** yanlış ya da kelime kelime çeviri anlamı (el sağlığı gibi).
    **1:** doğru ama eksik/dolambaçlı açıklama.
    **2:** doğru ve öz açıklama.

11. **Soru:** "'Kafayı yemek' deyimini bir cümlede kullan."
    **Beklenen:** "çıldırmak/çok sinirlenmek" anlamında doğal kullanım.
    **0:** deyimi yanlış anlamda kullanıyor (gerçekten kafa yemek gibi).
    **1:** anlam doğru ama cümle yapay/zorlama.
    **2:** doğal, günlük konuşmada geçebilecek cümle.

12. **Soru:** "Biri sana 'oha falso' yazdı, bu ne demek ve nasıl cevap verirsin?"
    **Beklenen:** şaşkınlık ifade eden argo olduğunu tanımalı, buna uygun rahat bir cevap vermeli.
    **0:** argoyu tanımıyor, alakasız yorumluyor.
    **1:** anlamı biliyor ama cevabı yapay/resmi.
    **2:** anlamı doğru yakalayıp doğal bir üslupla cevap veriyor.

13. **Soru:** "'Yağmur gibi yağdı' ile 'para gibi yağdı' arasındaki farkı anlat."
    **Beklenen:** mecaz kullanımını (bolluk/çokluk) fark etmeli.
    **0:** mecazı hiç anlamıyor, kelime anlamıyla açıklıyor.
    **1:** farkı kısmen görüyor ama açıklama karışık.
    **2:** mecazı net görüp kısaca doğru açıklıyor.

### Ek ve çekim hataları (14-17)

14. **Soru:** "'Kitap' kelimesine hem çoğul hem iyelik hem de hâl eki ekleyerek bir cümle kur (örnek: kitaplarımda)."
    **Beklenen:** ünlü uyumuna uygun doğru ek sırası (çoğul+iyelik+hâl).
    **0:** ek sırası yanlış ya da ünlü uyumu bozuk (kitaplarmda gibi).
    **1:** ekler doğru ama cümle yapay.
    **2:** doğru ekler, doğal cümle.

15. **Soru:** "'Görmek' fiilini olumsuz, soru ve geçmiş zaman ekleriyle birlikte çek (örnek: görmedin mi?)."
    **Beklenen:** doğru sondan eklemeli çekim, ünsüz/ünlü uyumu bozulmamalı.
    **0:** çekim yanlış (görmedınmı, görmediniz mi yerine bozuk biçim).
    **1:** çekim doğru ama örnek cümle yapay.
    **2:** doğru çekim, doğal örnek.

16. **Soru:** "'Gel-,git-,otur-' fiillerini '-ecek/-acak' gelecek zaman ekiyle çekimle."
    **Beklenen:** büyük ünlü uyumuna göre doğru ek (gelecek, gidecek, oturacak).
    **0:** ek uyumsuz (geliecek, gidacak gibi).
    **1:** ekler çoğunlukla doğru, bir tanesi hatalı.
    **2:** üçü de doğru çekilmiş.

17. **Soru:** "Yabancı bir kelime olan 'laptop'a Türkçe hâl eki ekleyerek bir cümle kur (örnek: laptopumu aldım)."
    **Beklenen:** kaynaştırma harfi ve ünlü uyumu doğru uygulanmalı.
    **0:** ek yanlış kaynaştırılmış (laptopim gibi).
    **1:** ek doğru ama cümle garip.
    **2:** doğru ek, doğal cümle.

### Özet, merak sorusu, ton (18-20)

18. **Soru:** Aşağıdaki metni tek cümlede özetle: "Dün akşam eve geç geldim çünkü otobüs saatlerce
    gelmedi, sonra yağmur başladı ve şemsiyem yoktu, sırılsıklam oldum ama neyse ki evde sıcak
    çorba beni bekliyordu."
    **Beklenen:** tek cümle, ana olayları kaybetmeden kısaltma.
    **0:** özet değil, metni aynen tekrarlıyor ya da alakasız.
    **1:** özet doğru ama cümle bozuk/eksik ek.
    **2:** doğal, tek cümle, doğru özet.

19. **Soru:** "Şu cümle üzerine iki cümlelik merak uyandıran bir soru sor: 'Dün gece garip bir ses duydum.'"
    **Beklenen:** tam iki cümle, doğal merak ifadesi.
    **0:** soru değil, ifade cümlesi ya da konudan kopuk.
    **1:** merak ifadesi var ama cümle sayısı/akışı bozuk.
    **2:** doğal, tam iki cümle, gerçekten merak uyandıran soru.

20. **Soru:** Şu metnin tonunu tek kelimeyle söyle: "Yapma ya, cidden mi kazandık?? İnanamıyorum
    şu an, resmen havalardayım!"
    **Beklenen:** "heyecanlı/sevinçli/coşkulu" gibi doğru ton tespiti.
    **0:** yanlış ton (örn. "üzgün", "sinirli") ya da anlamadan geçiştiriyor.
    **1:** doğru ton ama gereksiz uzun açıklama.
    **2:** tek kelime/kısa, doğru ton.
