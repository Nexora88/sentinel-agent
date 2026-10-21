# Otonom kod inceleme ve kuantum-sonrası kriptografi yol haritası

## Mevcut gerçeklik
MKAOS'un kod iyileştirme akışı öneri/diff üretimi ve insan incelemesine hazırlama aşamasındadır. Bu belge, otomatik hata teşhisi, projeye özel regresyon testi üretimi, izole doğrulama ve otomatik inceleme PR'ı için kabul kapılarını tanımlar; bunların tamamlandığı iddiası değildir.

## Güvenli otonom inceleme döngüsü
1. Hata/CI başarısızlığını değişmez bir olay kaydı ve commit SHA ile yakala.
2. İzole, ağ çıkışı kapalı, tek kullanımlık çalışma alanında tekrarlanabilir biçimde yeniden üret.
3. Hata izini ve ilgili dosyaları modele yalnızca sınırlı bağlam olarak ver; depo içeriğini güvenilmeyen veri say.
4. Hata için önce başarısız olan regresyon testi üret; testi yamadan önce çalıştır ve beklenen başarısızlığı kaydet.
5. En küçük yamayı uygula; regresyon testi, tüm test paketi, biçim/lint, tür kontrolleri ve güvenlik taramalarını çalıştır.
6. Testler başarısızsa döngüyü sınırlı sayıda denemede durdur; asla sonsuz düzeltme döngüsü kurma.
7. Başarılıysa yalnızca ayrı bir dalda taslak PR aç; diff, test kanıtı, riskler ve sağlayıcı/model sürümünü raporla.
8. Merge, release, sır erişimi, ağ erişimi ve dağıtım insan onayında kalır. CI çıktısı modelin talimatı değildir; prompt injection olarak değerlendir.

## Kabul ölçütleri
- Her çalıştırma benzersiz run ID, kaynak SHA, zaman aşımı ve kaynak limitlerine sahip.
- Araç izin listesi ve çalışma alanı sınırları testlerle doğrulanmış.
- Üretilen test, yamadan önce hatayı yakalıyor ve yamadan sonra geçiyor.
- İlgisiz dosyalara dokunulmuyor; sırlar log ve PR içeriğinden redakte ediliyor.
- CI sonucu başarısız/eksikse PR otomatik olarak merge edilemiyor.
- PR oluşturma ayrı, dar kapsamlı GitHub izniyle ve insan denetimiyle açılıyor.

## Kuantum-sonrası kriptografi (deneysel)
NIST standartları ML-KEM (FIPS 203) anahtar kapsülleme ve ML-DSA (FIPS 204) dijital imza içindir. Bunlar farklı amaçlara sahiptir: ML-KEM imza yerine geçmez; Ed25519 da gizlilik/şifreleme sağlamaz. Yeni `core/post_quantum.py` yalnızca isteğe bağlı sağlayıcı yetenek kontrolüdür; veri şifrelemesi veya imza üretimi gerçekleştirmez.

- Varsayılan profil kapalıdır: `MKAOS_PQ_PROFILE=disabled`.
- Deneysel profil: `MKAOS_PQ_PROFILE=experimental`; sağlayıcı veya algoritma yoksa açık hata verir, klasik kriptografiye sessiz geri dönüş yapmaz.
- Hedef algoritmalar: ML-KEM-768 ve ML-DSA-65. Gerçek entegrasyon öncesi bağımlılık sürüm/hash sabitleme, FIPS uyumluluk değerlendirmesi, test vektörleri, birlikte çalışabilirlik, anahtar saklama/rotasyon/iptal, protokol sürümleme ve tehdit modellemesi gerekir.
- `MKAOS_ENCRYPT_MEMORY_FILES` davranışı bu değişiklikle değiştirilmez. Bellek şifrelemesi için ayrıca sürümlü dosya biçimi, anahtar geçişi, bozuk dosya davranışı ve geri yükleme testleri gerekir.
- “Quantum-ready” veya “FIPS validated” iddiası yapılmamalıdır; bu profil üretime hazır değildir.

## Ses profilleri: Gökçe ve Metehan
Arayüzdeki gösterim adları Gökçe (kadın profili) ve Metehan (erkek profili) olabilir. İsim değişikliği gerçek ses modelini değiştirmez. Yerel Piper model kimlikleri ve dosya yolları yapılandırmadan çözülmeli; model yoksa açık hata verilmeli, yanlış sese sessiz düşülmemeli. Türkçe telaffuz, hız, lisans ve cihaz üstü ses kalitesi gerçek modellerle test edilmelidir.

## Hesap, ödeme ve canlı sağlayıcılar
Bunlar yalnızca arayüz ekleyerek tamamlanmış sayılmaz. Hesaplar için oturum güvenliği, parola sıfırlama ve e-posta doğrulama; ödeme için sağlayıcı webhook imzası, idempotency, test modu ve sır yönetimi; hava durumu/trafik için lisans, kota, zaman aşımı, cache, veri zaman damgası ve sağlayıcı kesintisi testleri gerekir. Sağlayıcı anahtarları istemciye gönderilmemelidir.


## Uygulama durumu — 2026-10-21

Bu dalda ilk güvenli dilim olarak:
- CI başarısız olduğunda çalışacak `.github/workflows/ci-failure-evidence.yml` eklendi. Varsayılan dalın güvenilir raporlama aracını kullanır; başarısız PR kodunu checkout edip çalıştırmaz, yalnızca 14 gün saklanan redakte edilmiş hata raporu üretir.
- `tools/ci_failure_report.py` logları sınırlar ve yaygın token/parola biçimlerini redakte eder; `tests/test_ci_failure_report.py` bu davranışları test eder.
- Arayüzde yerel Piper profilleri Gökçe (female) ve Metehan (male) olarak görünür. Bunlar yalnızca gösterim adlarıdır; ilgili Türkçe Piper modellerinin yerel olarak kurulması gerekir.

**Henüz tamamlanmamış:** otomatik izole yeniden üretim, yamadan önce başarısız olduğu kanıtlanan regresyon testi üretimi, en küçük yamanın otomatik uygulanması ve tam CI kanıtlarıyla otomatik taslak PR oluşturulması. Raporlama iş akışı bu işleri kendiliğinden yapmaz. Bunları eklemek için sır içermeyen, ağ çıkışı kapalı tek kullanımlık runner ve kısıtlı yerel kod modeli/araç yürütücüsü ayrı ayrı doğrulanmalıdır. Testler bu ortamda henüz çalıştırılmadı; bu nedenle yeşil CI veya başarılı regresyon iddiası yoktur.

## Ajan kafesi ve güvenlik sınırı

Ajanlar birbirinin talimatlarını güvenilir kabul etmemeli; yalnızca yapılandırılmış görev girdisi, kaynak SHA, izin listesi ve boyut/zaman limitleri paylaşmalıdır. Kod, issue metni, log, README ve test çıktıları güvenilmeyen veri kabul edilir; bunlardan gelen komutlar otomatik yürütülmez.

Önerilen üretim sınırları:
1. Planlayıcı/eleştirmen/uygulayıcı ayrı süreç ve ayrı kimliklerle çalışır; uygulayıcı yalnızca geçici çalışma alanına yazabilir.
2. Runner varsayılan olarak ağsız, sır erişimsiz, salt okunur kaynak + ayrı yazılabilir patch alanı ve CPU/RAM/zaman sınırlarıyla çalışır.
3. Dosya yolları izin listesiyle sınırlandırılır; symlink/path traversal, büyük dosya, binary ve gizli dosya değişimleri reddedilir.
4. Testler ağ erişimi ve üretim kimlik bilgileri olmadan çalışır; test başarısızlığı otomatik yeniden deneme sayısını sınırlar.
5. Ajanlar doğrudan `main`e push/merge yapamaz. PR oluşturma için ayrı, dar kapsamlı yetki gerekir; merge, release ve deploy insan onayında kalır.
6. Her karar, diff hash'i, test komutu/çıkış kodu, model sağlayıcısı-sürümü ve runner imajı değişmez bir kanıt raporuna yazılır.


**Etkinleşme notu:** GitHub `workflow_run` tetikleyicisi yalnızca varsayılan dalda bulunan iş akışını çalıştırır. Bu taslak PR birleştirilmeden, bu yeni kanıt iş akışı PR'ın kendi başarısız CI çalışmasını otomatik yakalayamaz; önce insan incelemesi gerekir. Birleştirme sonrası sonraki CI başarısızlıklarında etkinleşir.

Bu liste mimari kabul ölçütleridir; mevcut uygulamada tüm maddelerin sağlandığı anlamına gelmez.


## CI düzeltme yürütücüsü — ilk uygulama dilimi

`tools/ci_repair_executor.py` test-önce doğrulama denemelerini bir kerelik çalışma alanında yürütmek için eklendi. Ayrı bir regresyon-test yaması ve düzeltme yaması alır; önce regresyon testinin başarısız olduğunu, sonra düzeltmeden sonra aynı testin ve tam test komutunun başarılı olduğunu kanıtlamadan başarılı rapor üretmez.

- Kaynak geçici bir dizine kopyalanır; `.git`, `.env*`, model ve bellek dizinleri kopyalanmaz.
- Testler yalnızca SHA-256 özetiyle sabitlenmiş Docker imajında; `--network none`, salt okunur kök dosya sistemi, kapalı Linux yetenekleri, PID/RAM/CPU sınırları ve ayrı geçici alanla çalışır.
- Komutlar shell metni değil, doğrulanmış argv listeleridir. Yalnızca Python unittest/pytest, Node sözdizimi denetimi ve Cargo test komutları kabul edilir.
- Yama yolları proje izin listesiyle sınırlandırılır; gizli dosya/anahtar yolları, path traversal ve sembolik bağlantı üzerinden yazma reddedilir.
- Kanıt raporu komutları, dönüş kodlarını, süreleri ve yama hash'lerini içerir. Bu araç commit, push, PR, merge veya dağıtım yapmaz.

**Sınır:** Bu, güvenli yürütme katmanıdır; henüz başarısız GitHub Actions adımını kendi başına indirip aynen yeniden üretmez, LLM ile test/düzeltme yamalarını otomatik üretmez veya taslak PR açmaz. Yama ve komutları şu an güvenilir bir üst katman sağlamalıdır. Bu sınırlar çözülmeden tam otonom onarım iddiası yapılmamalıdır.


## Canlı veri ve ödeme test dilimi — 2026-10-21

- \`core/live_data.py\` gerçek Open-Meteo hava durumu ve TomTom trafik akışı adaptörleri sağlar. Ağ modu ve her özellik için ayrı opt-in zorunludur; koordinatlar doğrulanır, sağlayıcı yanıtı/observation timestamp'i ve çekim zamanı döndürülür, kısa TTL önbelleği vardır. TomTom API anahtarı yoksa trafik başarısız olur; sahte veya tahmini trafik verisi üretilmez.
- \`GET /api/live/weather\` ve \`GET /api/live/traffic\` kimlik doğrulamalıdır. Varsayılan Compose profili çevrimdışı kalır. \`docker-compose.networked.yml\` yalnızca ağ yolunu açar; her \`ALLOW_*\` izni ayrıca açıkça etkinleştirilmelidir.
- \`core/billing.py\` Stripe-hosted Checkout test akışı, imza/zaman damgası doğrulamalı webhook ve SQLite olay tekilleştirmesi ekler. Kart bilgisi MKAOS'a girmez; \`sk_live_\` anahtarları reddedilir. \`POST /api/billing/checkout\`, \`GET /api/billing/status\` ve \`POST /api/billing/webhook\` uç noktaları eklendi.
- Bu entegrasyonlar kod ve test seviyesinde hazırlanmıştır; gerçek sağlayıcı anahtarları, TomTom lisans/kota doğrulaması, Stripe test hesabı/price/webhook yapılandırması ve uçtan uca canlı bağlantı bu ortamda doğrulanmış değildir. Gerçek tahsilat desteklenmez. Hesap sistemi mevcut kimlik doğrulama/passkey katmanını kullanır; e-posta doğrulama/parola sıfırlama ve üretim ödeme operasyonları ayrı tamamlanmalıdır.
