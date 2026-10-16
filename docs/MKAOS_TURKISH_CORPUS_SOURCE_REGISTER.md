# MKAOS Türkçe korpus kaynak ve lisans sicili

**Durum:** İlk kaynak incelemesi tamamlandı; gerçek veri sürümü bazında hukuk/izin onayı henüz tamamlanmadı. Bu belge hiçbir kaynağı otomatik olarak eğitim için onaylamaz.

**İnceleme tarihi:** 2026-10-16  
**Kapsam:** Türkçe metinlerin MKAOS eğitim/doğrulama/test verisi olarak kullanılması, yeniden dağıtım ve model ağırlıklarının yayımlanması.

## Kaynak sicili

| Kaynak | Birincil şart/lisans kanıtı | İnceleme sonucu | Karar |
|---|---|---|---|
| Mozilla Common Voice — metin cümleleri | [Common Voice repository: licensing and content source](https://github.com/common-voice/common-voice) | Depo açıklaması, `server/data` altındaki cümlelerin çoğunun CC0 olduğunu bildiriyor. Bu açıklama, tek başına belirli bir yayımlanmış Türkçe veri sürümünün tüm dosyalarının, transkriptlerinin, seslerinin veya model ağırlıklarının koşullarını kanıtlamaz. Sürüm, Türkçe alt küme, dosya SHA-256 değerleri ve ilgili sürümün şartları ayrı kaydedilmeli. | **Aday — beklemede.** Yalnızca sürümü ve her dosyanın kapsamı doğrulanıp insan incelemesiyle kabul edilirse metin cümleleri kullanılabilir. Ses dosyaları bu metin izninin kapsamına dahil sayılmaz. |
| Türkçe Wikipedia / Wikimedia metni | [Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Terms_of_Use); [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Wikimedia metinlerinde atıf ve ShareAlike koşulları bulunur; sayfa geçmişi, içe aktarılmış içerik ve istisnalar kaynak bazında önemlidir. Veri lisansı ile eğitim sonucu ağırlıkların lisans/atıf yükümlülüğü aynı soru değildir. | **Eğitim için engelli.** Model eğitimi, ağırlıkların dağıtımı ve atıf/ShareAlike uyumluluğu hakkında yazılı hukuk incelemesi yapılmadan içeri alınmayacak. |
| Tatoeba Türkçe cümleleri | [Tatoeba downloads and data licensing](https://tatoeba.org/en/downloads); [Using the Tatoeba Corpus](https://en.wiki.tatoeba.org/articles/show/using-the-tatoeba-corpus) | Metin cümleleri genel olarak CC BY 2.0 FR koşuluna tabidir; katkı sahibi atfı gerekir. Cümle bazında CC0/başka lisanslar ve ses lisansları ayrı olabilir. İncelenen CC0 dil listesinin Türkçe için uygun bir alt küme sağladığı doğrulanmadı. | **Eğitim için engelli.** Cümle bazlı yazar/atıf bilgisini kaybetmeden kullanma ve eğitim/ağırlık dağıtım uyumluluğu yazılı olarak onaylanana kadar içeri alınmayacak. |

## Kabul edilecek kaynak için zorunlu kanıtlar

Her sürüm ve dosya için:

1. Kaynağın kanonik URL'si, tam sürüm/revizyonu, edinim tarihi ve SHA-256.
2. İlgili sürüme uygulanan lisansın metni ve lisansın hangi dosyalara uygulandığı.
3. Eğitim, türetilmiş veri oluşturma, ticari kullanım ve model ağırlıklarını dağıtma koşullarının ayrı değerlendirmesi.
4. Atıf metni, yazar/kaynak kimliklerinin korunma yöntemi ve ShareAlike gibi ek yükümlülükler.
5. Kişisel veri, hassas veri, gizli bilgi ve kişilerin hakları açısından insan incelemesi.
6. İnceleyen kişi, tarih, karar, gerekçe ve varsa hukuk danışmanı görüşünün referansı.
7. Kabul edilen kayıtların konu/dil/kalite kontrolü ve kopya/benzer içerik taraması.

**Kural:** Lisansın adı veya bir veri kümesinin “open” diye tanımlanması tek başına onay değildir. Otomatik metadata kontrolleri hukuki izin, kaynak kalitesi veya model yeteneği kanıtı sayılmaz.

## Veri bölme politikası

- Bölme, tek tek satırlar yerine mümkün olduğunda **kaynak/doküman grubu bazında** yapılır; aynı kaynak veya belge ailesinin kopyaları train ve test arasında dağılmaz.
- Hedef oranlar: train %80, validation %10, bağımsız test %10. Kaynak grubu sayısı küçükse oranlar yerine sızıntıyı önleme ve her bölümde yeterli örnek bulunması önceliklidir.
- **Train:** yalnızca eğitim ağırlıklarını güncellemek için.
- **Validation:** hiperparametre, checkpoint ve eğitim süresi seçimi için; bağımsız test sonucu burada kullanılmaz.
- **Test:** eğitim, prompt ayarı, model seçimi ve hata düzeltme kararlarından ayrı tutulur. Sonuçlar yalnızca dondurulmuş model adayı için alınır.
- Her bölüm için içerik hash'i, örnek sayısı, kaynak/lisans dökümü ve manifest hash'i raporlanır.
- Bölümler arasında tam/normalleştirilmiş kopya veya belge ailesi sızıntısı bulunursa eğitim engellenir.

## Şimdiki sonuç

Bu incelemede **eğitim için nihai olarak onaylanmış, sürümü sabitlenmiş bir Türkçe korpus henüz yoktur**. Bu yüzden sahte örnekler, uydurma lisans onayı veya sentetik “gerçek veri” eklenmez; mevcut eğitim aracı gerçek yerel veriler ve kanıtlar sağlanana kadar kapalı kalmalıdır.

Kaynak şartları değişebileceği için, veri edinildiği gün tekrar kontrol edilmeli ve sürüm bazlı kanıtlar sicile eklenmelidir. Bu belge hukuk danışmanlığı değildir.
