# Gizlilik, Kimlik Doğrulama ve Güvenli Gelişim Yol Haritas

Bu belge hedef mimari ve kabul kapısıdır; uygulanmamış özellikler varmış gibi sunulamaz.

## 1. Şifreleme katmanları

- **Ağda:** Uzak bağlantılar TLS 1.2+ (tercihen TLS 1.3) kullanmalı; sertifika doğrulaması kapatılmamalı. Yerel makinedeki HTTP loopback trafiği internetten erişilebilir bir servise açılmamalı. Uzaktan erişim için açıkça yapılandırılmış HTTPS reverse proxy/VPN kullanılmalı.
- **Diskte:** core/encrypted_store.py, AES-256-GCM ile tekil hassas dosyaları şifreleyebilen atomik bir temel sağlar. Anahtar MKAOS_MEMORY_KEY üzerinden, veri dizininin dışında sağlanır. Anahtar yoksa veya doğrulama başarısızsa veri okunmaz ve sıfırlanmaz.
- **Sınır:** Bu dosya sınıfı tek başına ChromaDB/RAG dizinini, SQLite veritabanlarını, yüklemeleri, günlükleri veya yedekleri şifrelemez. Bu yollar ayrı ayrı bağlanıp test edilene kadar “tüm bellek şifreli” denemez.
- **Anahtar yönetimi:** Üretimde uzun ömürlü anahtarın düz metin .env dosyasında tutulması tercih edilmemeli. OS keychain/credential vault veya TPM/secure-enclave tabanlı sağlayıcı eklenmeli. Anahtar kaybında kurtarma yolu ve şifreli yedek prosedürü tanımlanmalı; anahtar depoyla birlikte yedeklenmemeli.
- **Geçiş:** Eski ortak memory/ dizini otomatik olarak yeni kullanıcılara taşınmaz. Önce yedek alınır, sahiplik bağımsız doğrulanır, kullanıcı onayı alınır; sonra ayrı ve geri alınabilir bir taşıma aracıyla şifrelenir. Düz metin kalıntıları, snapshot'lar ve yedekler ayrıca ele alınır.

## 2. WebAuthn / Passkeys

Hedef akış:
1. Sunucu her kayıt ve doğrulama için kriptografik rastgele, kısa ömürlü, tek kullanımlık challenge üretir.
2. Challenge, origin ve RP ID doğrulanır; challenge tekrar kullanımına izin verilmez.
3. Kimlik bilgisi kullanıcı hesabına bağlanır; public key sunucuda tutulur, özel anahtar donanım/işletim sistemi kimlik doğrulayıcısında kalır.
4. Kimlik bilgisi kaldırma, yeni cihaz ekleme ve kurtarma için mevcut oturum + açık kullanıcı onayı gerekir.
5. WebAuthn yüksek riskli işlemler (dış ağa erişim, repo değişikliği, veri dışa aktarma, anahtar değiştirme) için ek onay olabilir; kendi başına her isteği otomatik yetkilendirmez.
6. Geliştirme/test origin'i ile üretim origin'i ayrılır; HTTPS ve origin kontrolleri zorunludur.

Bu belge tek başına WebAuthn endpoint'lerinin uygulandığı anlamına gelmez. Uygulama için kayıt/oturum açma rotaları, challenge deposu, rate limit, kurtarma akışı ve negatif testler gereklidir.

## 3. Güvenli web araştırması ve eklentiler

- Web okuma varsayılan olarak kapalı veya kullanıcı tarafından açılan, denetlenebilir bir izin olmalıdır.
- İzinli alan adları, zaman aşımı, yanıt boyutu, MIME türü ve yönlendirme sayısı sınırlanır; DNS/IP yeniden çözümleme ve SSRF koruması uygulanır.
- Sayfalardan alınan içerik güvenilmeyen veri sayılır; sayfa metni sistem talimatı veya eklenti komutu olarak çalıştırılmaz.
- Yalnızca kullanıcıya ait veya açıkça yetkilendirilmiş sistemlerde savunma amaçlı güvenlik kontrolü yapılır. İzinsiz açık taraması, kimlik bilgisi toplama, zararlı yazılım, kalıcılık, gizlenme ve istismar zinciri üretimi ürün kapsamı dışındadır.
- Her eklenti en az yetkiyle çalışır; izinleri, ağ hedefleri, dosya erişimi ve yan etkileri görünürdür. İşlem öncesi onay, denetim kaydı ve iptal mekanizması bulunur.

## 4. Sürekli gelişim: otomatik öğrenme, kontrollü yayın

- Saatlik/günlük görevler yalnızca cihaz açıkken ve kullanıcı bu planı etkinleştirdiyse çalışır.
- Bilgi toplama, kaynak/başlık/tarih/lisans kaydı, yerel indeksleme ve değerlendirme ayrı aşamalardır.
- Her yeni bilgi için kaynak, güven düzeyi, çelişki ve tekrar kontrol edilir. Web sayfaları doğrudan güvenilir bellek veya kod olarak kabul edilmez.
- Model ağırlıkları veya çekirdek kod kendiliğinden sessizce değiştirilmez. Aday değişiklikler test, kalite kıyaslaması, güvenlik taraması ve insan onayıyla PR olarak sunulur.
- Gelişim metrikleri sürümlenir; başarısız değerlendirme önceki kararlı sürüme dönüşü tetikler. “Her saat daha akıllı” gibi ölçülmemiş bir iddia kullanılmaz.

## 5. Ses, görsel ve video

- Öncelik yerel/öz barındırılan adaptörlerdir; açıkça etkinleştirilmedikçe herkese açık üretim API'sine düşülmez.
- Ses için yerel STT/TTS, görsel için yerel görüntü modeli, video için gerçek yerel video hattı ayrı ayrı doğrulanır. Paket kurulmuş olması gerçek çıkarım kanıtı değildir.
- Her adaptör donanım, model adı/sürümü, lisans, bellek ihtiyacı ve çıktı yolunu raporlar. Donanım yetersizse görev bekletilir veya açıkça reddedilir.
- Kullanıcı yüklemeleri doğrulanır; boyut ve biçim sınırları uygulanır. Medya işleri kullanıcıya bağlanır ve diğer kullanıcıların çıktılarına erişemez.

## 6. Kabul kapıları

- Şifreleme: doğru anahtarla round-trip; yanlış anahtar ve değiştirilmiş ciphertext reddi; diskte açık metin bulunmaması.
- Entegrasyon: RAG, profil, medya kuyruğu, yükleme, log ve yedeklerin her biri için ayrı şifreleme/erişim testi.
- WebAuthn: yanlış origin, yanlış challenge, süresi geçmiş/tekrar kullanılan challenge ve yanlış imza testleri.
- Ağ: TLS sertifika doğrulama, SSRF/DNS rebinding ve allowlist testleri.
- Güvenli gelişim: onaysız kod/deploy/yayın olmadığını kanıtlayan test.
- Medya: gerçek hedef donanımda başarılı yerel çıkarım ve ağ kapalıyken kanıt.
