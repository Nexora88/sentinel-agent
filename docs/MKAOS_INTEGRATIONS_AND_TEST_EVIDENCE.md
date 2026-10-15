# MKAOS entegrasyonları, yerel medya ve test kanıtı

## Bu değişikliğin sağladığı şey
- Entegrasyonların yapılandırma durumunu gizli değerleri göstermeden raporlayan bir katalog.
- Ağ kapalıyken dış servis eylemlerini reddeden, bilinmeyen eylemlerde kapalı kalan bir yetkilendirme sınırı.
- Dış sistemde yazma/değişiklik işlemlerine açık onay şartı.
- Linux, Windows ve macOS üzerinde standart kütüphane tabanlı uyumluluk testlerini çalıştıran CI matrisi.

Bu katalog entegrasyonların gerçekten bağlandığı veya API çağrılarının tamamlandığı anlamına gelmez. configured_unverified yalnızca gerekli ayarların bulunduğunu ifade eder; bağlantı, kimlik doğrulama, izin kapsamı veya API başarısı ölçülmüş değildir. Her bağdaştırıcı kendi uçtan uca testiyle doğrulanmalıdır.

## Entegrasyon gerçeklik tablosu
| Alan | Beklenen yöntem | Çevrimdışı davranış | Kanıt gereksinimi |
|---|---|---|---|
| GitHub | Var olan GitHub istemcisi + sınırlı token | Engellenir | Test deposunda issue/branch/PR uçtan uca testi; yazma öncesi onay |
| Canva | Yetkili Canva API/uygulama erişimi | Engellenir | OAuth/token ve test tasarımı oluşturma/export denemesi |
| E-posta | Kullanıcının seçtiği SMTP/sağlayıcı | Engellenir | Test kutusuna gönderim; alıcı ve içerik için onay |
| Google finans | Yetkili veri sağlayıcı adaptörü | Engellenir | Sağlayıcı/API lisansı ve kaynak-zaman damgası doğrulaması |
| TradingView | Yetkili erişim; lisans koşullarına uygun | Engellenir | Yetki ve kullanım koşulları; izinsiz kazıma yok |
| Hava durumu | Belgelenmiş API veya önbellek | Önbellek dışında canlı veri yok | Kaynak, güncelleme zamanı ve lisans atfı |
| Supabase | Kullanıcıya özel RLS ve en az ayrıcalık | Bulut verisi erişilemez | İki kullanıcı arasında izolasyon testleri; service-role istemciye verilmez |
| Vercel | Yetkili token ve sınırlı proje kapsamı | Engellenir | Önizleme dağıtımı, log/health check, geri alma planı |
| Ses/görsel/video | Yerel STT/TTS, yerel görsel modeli, FFmpeg | Modeller/araçlar önceden kuruluysa yerel çalışır | Gerçek medya örnekleri, model hash/lisansı, ağ çıkışı gözlemi |

## Wi-Fi kapalı ve ana bilgisayar düzeyinde ağ testi
1. Test cihazına modelleri ve bağımlılıkları önceden kur; sonra Wi-Fi ve diğer ağ arayüzlerini kapat.
2. Yerel sohbet, dosya analizi, ses çözümleme, TTS, görsel üretimi ve video oluşturmayı ayrı ayrı çalıştır. Bir özelliğin arayüzde görünmesi çalıştığına kanıt değildir.
3. Testi işletim sistemi güvenlik duvarı veya izole ağ namespace'i ile çalıştır; süreç ağ bağlantılarını ve DNS isteklerini paket/bağlantı gözlemiyle kaydet. Sadece uygulama ayarı veya Docker Compose profili tek başına kanıt sayılmaz.
4. Ağ kapalıyken dış entegrasyonların fail-closed kaldığını doğrula. Sonuç commit, OS sürümü, donanım, model dosyası SHA-256, başlangıç/bitiş zamanı ve gözlenen çıkış bağlantılarını içermeli.
5. CI matrisi gerçek donanımda GPU, Android yerel LLM veya Wi-Fi kapalı testi yapmaz; bunlar ayrı cihaz testleri olarak raporlanmalıdır.

## Türkçe kalite ve model kökeni
- Türkçe yazım, yönerge takibi, özetleme, dosya içeriğini doğru aktarma, tarih/sayı ve güvenli reddetme için sabit görev kümesi kullan.
- Her çalıştırmada model adı/sürümü, nicemleme, lisans URL'si, ağırlık SHA-256'sı, üretici/menşe bilgisi (yalnızca doğrulanabildiği kadar), cihaz, gecikme ve bellek kullanımı kaydedilsin.
- Türkçe çıktı vermek, modelin Türkiye'de geliştirildiğini veya eğitim verisinin yerli olduğunu kanıtlamaz. Doğrulanamayan menşe alanları bilinmiyor olarak kalmalıdır.

## Yerel medya
Mevcut ses, görsel ve video modüllerinin kullanılabilmesi için yerel model ağırlıkları ve haricî programlar kurulmuş olmalıdır. Model indirme işlemi çevrimdışı çalışma kanıtı değildir; ağ kapatıldıktan sonra ayrı test yapılmalıdır. Görsel üretim arka ucu yoksa dış servise otomatik kaçış yapılmamalıdır.
