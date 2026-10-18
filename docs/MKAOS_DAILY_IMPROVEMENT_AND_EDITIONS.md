# MKAOS — günlük gelişim, çevrimdışı çalışma ve donanım sürümleri

Bu belge ürün sözleşmesidir. Bir hedefi tamamlanmış özellik gibi göstermeyin; her sürüm için test ve ölçüm kanıtı gerekir.

## 1. Günlük gelişim döngüsü

GitHub Actions günlük kalite döngüsü; testleri, güvenlik kontrollerini ve sentetik Rust CPU ölçümünü tekrarlar. Başarısızlıkta takip edilebilir bir GitHub issue oluşturur. Bu otomasyon tek başına kodu değiştirmez, PR birleştirmez, sırları okumaz ve model eğitmez. Kod değişikliği önerileri ayrı bir PR, testler ve insan incelemesi gerektirir. Böylece bozuk bir otomatik değişiklik her gün ana dala yayılamaz.

- Önce regresyon testi ve güvenlik taraması.
- Sonra aynı donanım/işletim sistemi koşullarında kıyaslanabilir performans ölçümü.
- Her bulguya log, commit SHA, test sonucu ve tekrar üretme adımı eklenir.
- Bir günlük başarısızlık geçmişteki başarılı testleri geçersiz kılmaz; release kapıları yeniden çalıştırılır.
- Otomatik düzeltme önerileri hiçbir zaman onay kapılarını, veri kaynağı lisans denetimini veya ağ politikalarını değiştiremez.

## 2. Çevrimdışı ve kesintiye dayanıklı çalışma

- Varsayılan: yerel dosyalar, yerel indeks, yerel model ve loopback erişimi. Kullanıcı açıkça seçmedikçe dış ağa istek gönderilmez.
- İnternet yokken sohbet, yerel belgeler, geçmiş ve önceden kurulu araçlar çalışmayı sürdürmelidir; bulut tabanlı araçlar “kullanılamıyor” olarak açıkça gösterilir, sahte sonuç üretmez.
- Paketler ve model dosyaları çevrimiçiyken indirilir; SHA-256 ve sürüm manifesti doğrulanır. Kurulum dosyaları ve model ağırlıkları internetsiz taşınabilir bir klasöre kopyalanabilir.
- Güncelleme atomik olmalı: indirme/ doğrulama başarısız olursa çalışan sürüm korunur; son iyi sürüme geri dönüş bulunur.
- Offline testi ağ erişimini yalnızca uygulama düzeyinde değil, işletim sistemi/container sınırında da doğrulamalıdır. “Docker internal” tek başına tam air-gap kanıtı değildir.
- Hiçbir günlük gelişim işi, internet yokken uzak servis gerektiren bir görevi sonsuza kadar bekletmemeli; sınırlı zaman aşımı, yerel kuyruk ve yeniden deneme kullanmalıdır.

## 3. Donanım sınıfları

Sınıflar pazarlama etiketi değil, ölçülebilir kaynak profilleridir. RAM tek başına modelin çalışacağını garanti etmez; model boyutu, kuantizasyon, bağlam uzunluğu, işletim sistemi ve GPU VRAM'i de kontrol edilir.

| Sürüm | Başlangıç profili | Varsayılan davranış |
|---|---|---|
| **MKAOS Minimal** | 2–4 GB RAM, CPU, düşük depolama | Ağsız çekirdek araçları, kısa bağlam, küçük yerel indeks; sohbet modeli uygun değilse açıkça devre dışı |
| **MKAOS Core** | 8 GB RAM, CPU veya paylaşımlı grafik | Küçük kuantize model için uygunluk kontrolü; kısa/orta bağlam ve sınırlı eşzamanlılık |
| **MKAOS Plus** | 16 GB RAM, modern CPU veya giriş GPU | Daha büyük kuantize modeller; VRAM ve bellek ölçümü geçmeden GPU vaadi yok |
| **MKAOS Workstation** | 32 GB+ RAM ve/veya yeterli VRAM | Daha uzun bağlam ve daha büyük modeller; backend doğrulaması zorunlu |
| **MKAOS Portable** | ARM64 veya x86-64, kısıtlı kaynak | Platforma özel derleme ve uyum testleri; GPU desteği varsayılmaz |

Sürüm seçici önce CPU mimarisi, OS, RAM, boş disk, GPU adı ve VRAM'i salt-okunur şekilde tespit eder. Bilinmeyen GPU “unknown” olarak kalır; donanım bilgisi tespit etmek için ağa çıkılmaz. Kullanıcı profili elle değiştirebilir. Otomatik profil daha büyük model indirip kurmaz.

## 4. Tek tuşla kurulum sözleşmesi

- Windows: imzalı PowerShell kurucusu; Linux: shell kurucusu; macOS: doğrulanmış paket/kurucu. Her biri aynı manifesti kullanır.
- “Kurulum” ile “model indirme” ayrı onaylardır. İlk kurulum internet gerektirebilir; çevrimdışı paket seçeneği önceden indirilmiş imzalı/özet doğrulamalı varlıklarla çalışır.
- Kurucu önce sistem gereksinimini denetler, seçilen sürümün hash'leri doğrulanmış bileşenlerini kurar, health-check çalıştırır ve kaldırma/geri alma adımlarını sunar.
- İdari yetki yalnızca gerçekten gerekiyorsa istenir. Gizli parola, token veya API anahtarı terminale/loga yazılmaz.
- Kurucu başarısızsa kısmi kurulumu temizler ve nedeni gösterir. İndirme URL'si, sürüm, lisans ve SHA-256 manifestte bulunmadan model indirilmez.
- Docker kolay yolu olabilir ancak Minimal sürümün tek seçeneği olmamalıdır. Kaynak kısıtlı cihazlar için yerel Rust CLI ve isteğe bağlı arayüz paketi hedeflenir.

## 5. Siber güvenlik, bilim ve Atatürk ilkesi

MKAOS; bilimi ölçülebilir deney, tekrarlanabilir sonuç, kaynak gösterme ve belirsizliği dürüstçe belirtme olarak uygular. Atatürk'ün bilim, akıl, eğitim ve üretim vurgusu ürünün öğrenme/araştırma yaklaşımına rehberdir; teknik doğrulamanın yerine geçmez.

- Savunmacı güvenlik: bağımlılık taraması, sır taraması, en az yetki, güvenli varsayılanlar, denetlenebilir günlükler ve saldırı simülasyonu için izole testler.
- Kullanıcı verileri yerel varsayılanla saklanır; isteğe bağlı senkronizasyon açıkça belirtilir ve tenant sınırları test edilir.
- Eğitim sadece insan tarafından lisans, gizlilik, atıf ve kullanım izni onaylanmış kaynaklardan açılır. Günlük otomasyon bu kilidi aşamaz.
- Metrikler sentetik model hızını gerçek model kalitesi olarak sunamaz. Referans model testi MKAOS'un kendi ağırlıklarının yeteneği sayılmaz.

## 6. Yayın kapıları

Bir sürümün “hazır” denebilmesi için: OS/CPU matrisi, kurulum ve kaldırma testi, ağ kesintisi testi, hash kontrolü, güvenlik regresyonları, tokenizer-checkpoint uyumu, RAM/VRAM tepe ölçümü ve Türkçe bağımsız değerlendirme raporu gerekir. Desteklenmeyen donanımda düzgün hata vermek de başarılı bir uyumluluk sonucudur.
