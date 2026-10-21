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
