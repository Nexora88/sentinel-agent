# MKAOS güvenlik, cihaz ve çevrimdışı doğrulama kapıları

Bu belge tamamlanmış sonuçları değil, uygulanacak kabul testlerini ve kanıt biçimini tanımlar. Test kaydı yoksa özellik **doğrulanmadı** sayılır.

## Çok kullanıcılı izolasyon
- Her kullanıcı için ayrı bellek koleksiyonu/dizini, yükleme alanı, üretilen medya, iş kuyruğu ve dışa aktarma yetki sınırı gerekir.
- Kimlik yalnızca istemcinin gönderdiği kullanıcı adıyla alınmamalı; doğrulanmış oturumdan türetilmelidir.
- Olumlu test: A kullanıcısı kendi dosya/bellek kayıtlarını okuyup yazabilir.
- Negatif test: B kullanıcısı A'nın dosya kimliği, dosya yolu, bellek sorgusu, medya adı ve iş kimliğiyle erişim denediğinde 403/404 alır; içerik, boyut veya varlık bilgisi sızmaz.
- Eşzamanlılık testi: iki kullanıcı paralel yükleme/sorgu yaptığında kayıtlar karışmaz.
- core.tenant_storage güvenli yol ilkelleri ve birim testleri sağlar. Bu, mevcut tüm RAG, yükleme, medya, plan ve iş kuyruğunun çok kiracılı geçişinin tamamlandığı anlamına **gelmez**. Uygulama entegrasyonu tamamlanmadan çok kullanıcılı izolasyon tamamlandı işaretlenmemelidir.

## Android ve GPU
Android istemci uygulaması testi; Android cihazda Ollama/llama.cpp gibi bir motorla yerel model çalıştırma testinden ayrıdır. Her ikisi için cihaz modeli, OS sürümü, runtime/model sürümü, ağırlık SHA-256, ilk token/gecikme, bellek, hata ve çevrimdışı sonuç kaydedilmelidir.
- CPU: gerçek CPU çıkarımı ve RAM/ısı/latency.
- NVIDIA: sürücü, CUDA/runtime, GPU adı, GPU belleği ve doğrulanmış GPU üzerinde çıkarım.
- AMD: ROCm/runtime, GPU adı/belleği ve doğrulanmış çıkarım.
- Apple: macOS sürümü, Metal/MLX/Core ML veya kullanılan backend ve doğrulanmış çıkarım.
CI'da bir işletim sistemi üzerinde test geçmesi GPU doğrulaması değildir. Gerçek donanım veya uygun self-hosted runner kanıtı olmadan bu matris tamamlanmış sayılmaz. scripts/device_validation.py tanılama raporu üretir; tek başına çıkarım doğrulamaz.

## Çevrimdışı ve host-level ağ çıkışı
1. Model ve bağımlılıkları kur; sonra Wi-Fi yanında Ethernet, mobil tethering, VPN ve diğer çıkış yollarını da kapat veya host firewall ile açıkça engelle.
2. Yerel sohbet, dosya okuma, yerel STT/TTS, yerel görsel ve video görevlerini ayrı ayrı çalıştır.
3. İşletim sistemi firewall/packet capture/connection audit çıktısını ve zaman aralığını kaydet. Yalnızca MKAOS_NETWORK_MODE=offline, UI rozeti veya Docker profili kanıt değildir.
4. Aynı testte DNS ve süreç bağlantıları ölçülmeli; beklenmeyen dış hedef varsa test başarısız.
5. Kanıt paketi: commit SHA, cihaz/OS, firewall kuralı, gözlem aracı/çıktısı, model hash'leri, görev sonuçları ve başlangıç-bitiş zamanı.

## Entegrasyonlar ve ajanlar
Her bağdaştırıcı için test ortamı, en az ayrıcalıklı OAuth/token kapsamı, salt-okunur test ve yazma öncesi kullanıcı onayı, idempotency/timeout davranışı, sonuç doğrulaması ve denetim kaydı gerekir. configured_unverified yalnızca yapılandırma bulunduğunu söyler; API bağlantısı ya da gerçek entegrasyon değildir. Canva, e-posta, Supabase, Vercel, hava durumu ve finans bağlantıları yetkili test ortamında ayrı ayrı doğrulanmalıdır. Gerçek sırları test çıktısına yazma.

## Türkçe ve model kökeni
- Başlangıç görevleri: tests/fixtures/turkish_quality_tasks.json; sonuçlar model/sürüm ve değerlendirme tarihiyle kaydedilmeli.
- Model kayıt şablonu: docs/model-provenance.template.json.
- Ağırlık SHA-256'sı dosyayı tanımlar; üretici, eğitim verisi veya ülke kökenini tek başına kanıtlamaz.
- Lisans URL'si, upstream depo ve köken kanıtı bağımsız kontrol edilmelidir. Belirsiz alanlar unverified/unknown kalmalıdır.

## Birleştirme kapısı
PR yalnızca otomatik testler başarılıysa ve değişiklik kapsamındaki güvenlik iddiaları dürüstçe sınırlandırılmışsa birleştirilebilir. Donanım, host firewall ve canlı dış API testleri GitHub-hosted CI'dan çıkarılamaz; bunlar ayrı kanıt raporları gerektirir.
