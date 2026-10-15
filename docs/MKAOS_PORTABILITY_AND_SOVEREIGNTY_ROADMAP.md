# MKAOS Çoklu Platform ve Dijital Egemenlik Yol Haritası

## Ürün hedefi
MKAOS tek bir geliştiricinin makinesine bağlı kalmamalı. Farklı kullanıcılar kendi cihazlarında çalıştırabilmeli; Türkçe öncelikli olmalı; önceden kurulmuş yerel modellerle internet kesildiğinde temel işlevlerini sürdürmeli. Egemenlik bir slogan değil, tekrarlanabilir testlerle desteklenen bir iddia olmalıdır.

## Tasarım ilkeleri
1. Yerel sohbet, yerel dosya bilgisi, kişisel bellek, temel planlama ve temel güvenlik kontrolleri; model/veri önceden kurulmuşsa ağsız çalışmalıdır.
2. Sohbet, dosya, bellek, anahtar ve onaylar kullanıcı kimliğine göre ayrılmalı; her istekte sunucu tarafında yetki kontrolü yapılmalıdır. Paylaşılan özel anahtar veya varsayılan yönetici hesabı olmamalıdır.
3. RAM, CPU mimarisi, işletim sistemi ve doğrulanmış hızlandırıcı adaptörleri algılanmalı. Kaynak yetmezse küçük modele veya kuralsal moda geçilmeli.
4. NVIDIA/CUDA, AMD/ROCm, Apple Metal ve CPU yolları ayrı adaptörlerle doğrulanmalıdır. GPU bulunması otomatik destek anlamına gelmez.
5. Android/iOS tarayıcıları yönetim istemcisi olabilir. Cihaz üzerinde LLM ancak desteklenen yerel çalışma zamanı ve yeterli kaynak varsa çalışır. Yerel ağdaki bir sunucuya bağlanmak, cihaz üzerinde bağımsız çalışma değildir.
6. Dış ağ entegrasyonları kapalı ve ayrı izinlerle açılır olmalı. Çevrimdışı profilde uygulama ve model adaptörleri dış uç noktalara erişmemelidir.
7. Arayüz, hata mesajları, kurulum, güvenlik raporları ve belgeler Türkçe öncelikli olmalı; İngilizce ikincil dil olabilir. Türkçe kalite gerçek görevlerle ölçülmelidir.
8. Güncelleme, model değiştirme, dış sisteme yazma ve sistem ayarı değişikliği açık kullanıcı onayı gerektirmelidir.

## Bu dalda eklenen altyapı
core/runtime_profile.py standart kütüphane ile işletim sistemi, mimari, CPU ve mümkün olduğunda toplam RAM bilgisini yerel olarak toplar. Ağ isteği yapmaz. RAM'e göre başlangıç model önerileri verir. GPU desteği doğrulanmadığından unknown olarak gösterilir. Bu modül henüz arayüze veya model yönlendiricisine bağlanmış otomatik model değiştirici değildir.

## Donanım profili: kaba başlangıç eşikleri
| Profil | Toplam RAM | Politika |
|---|---:|---|
| Minimal | 3 GB altı | LLM garantisi yok; temel kuralsal işlevler |
| Düşük | 3–6 GB | Çok küçük model yalnızca gerçek cihaz testinden sonra |
| Giriş | 6–12 GB | Küçük model; eşzamanlı uygulamalar dikkate alınır |
| Standart | 12–24 GB | 3B sınıfı model başlangıç denemesi |
| Yüksek | 24 GB ve üzeri | 7B sınıfı model denenebilir; VRAM/nicemleme önemlidir |

Bunlar kesin sistem gereksinimi değildir. Model boyutu, nicemleme, bağlam uzunluğu, önbellek, işletim sistemi ve boş RAM sonucu değiştirir. Her öneri gerçek model başlatma ve yanıt testiyle doğrulanmalıdır.

## Çok kullanıcılı mimari için zorunlu işler
- Güvenli kayıt/giriş, oturum iptali, parola saklama ve kaba kuvvet sınırlaması.
- Her kullanıcı için ayrı sohbet/bellek/dosya alanı ve kullanıcı kapsamlı sorgular.
- Sunucu tarafı sahiplik kontrolleri; istemciden gelen user_id tek başına yetki kanıtı değildir.
- Yönetici işlemlerinde en az ayrıcalık ve denetim kaydı.
- Kullanıcı başına kota; bir kullanıcının model yükü diğer kullanıcıları kilitlememeli.
- Veri dışa aktarma/silme ve yedekler/loglar için açık saklama politikası.
- A kullanıcısı B kullanıcısının sohbetini okuyamamalı, değiştirememeli veya silememeli testleri.

## Bağımsızlığı kanıtlama planı
1. Çevrimdışı profilde host seviyesinde dış DNS/HTTP/HTTPS çıkışı yakalanmalı ve engellenmeli. Sadece ortam değişkeni veya Docker ayarı yeterli kanıt değildir.
2. Wi-Fi/ağ kapalıyken önceden kurulmuş modellerle yerel sohbet, bellek ve planlama uçtan uca test edilmeli.
3. Temiz kurulumda model yoksa otomatik dış indirme yapılmamalı; Türkçe uyarı verilmeli.
4. Ağ istekleri, telemetri, hata raporları ve günlüklerde veri sızıntısı regresyon testleri çalışmalı.
5. Linux, Windows ve macOS için CI; Android için istemci ve yerel çalışma zamanı cihaz testleri olmalı.
6. CPU-only, CUDA, ROCm ve Metal yalnızca uygun gerçek donanımda test edilirse doğrulanmış sayılmalı; aksi durumda test edilmedi olarak raporlanmalı.
7. Türkçe görev kümesiyle cevap kalitesi, gecikme, RAM/VRAM ve model sürümü raporlanmalı.
8. Test raporu commit, ortam, ağ gözlemi ve sonuçları içermeli; test edilmeyen platformlar açıkça listelenmeli.

## Kabul kriterleri
- [ ] En az iki kullanıcıyla veri izolasyonu testleri geçiyor.
- [ ] Donanım profili ağ kullanmadan üretiliyor.
- [ ] CPU-only kurulumda çalışma veya kontrollü yetersiz kaynak durumu doğrulanıyor.
- [ ] İnternet kapalıyken temel yerel akışlar uçtan uca geçiyor.
- [ ] Host seviyesinde ağ çıkışı test ediliyor.
- [ ] Windows, Linux ve macOS sonuçları CI veya cihaz testleriyle raporlanıyor.
- [ ] Android istemci ve cihaz üstü model desteği ayrı etiketleniyor.
- [ ] Her GPU adaptörü gerçek donanımda test edilmeden destekleniyor sayılmıyor.
- [ ] Türkçe kalite sonuçları model ve donanım sürümüyle yayımlanıyor.

## “Tam Türk” hedefinin doğrulanabilir tanımı
Türkçe arayüz ve yerel veri kontrolünün yanında, Türkiye'de geliştirilen/denetlenen bileşenlere öncelik ve şeffaf tedarik zinciri hedeflenmelidir. Her modelin ağırlıklarının, lisansının, eğitim verisi kökeninin ve geliştirici ülkesinin doğrulanması gerekir. Türkçe konuşmak tek başına modelin Türk yapımı olduğunu kanıtlamaz.

Bu belge hedef ve doğrulama planıdır; bütün platformların veya ağ izolasyonunun şimdiden doğrulandığı anlamına gelmez.
