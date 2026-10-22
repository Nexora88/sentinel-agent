# MKAOS hızlı yerel model stratejisi

## Kısa karar

MKAOS'u pahalı API'lere bağlamadan geliştirmek doğru hedef. Ancak çok hızlı, genel amaçlı, güçlü, hiç parametresi ve eğitimi olmayan kendi dil modeli teknik olarak mümkün değil: doğal dilde genelleme için ya öğrenilmiş ağırlıklar ya da sınırlı, açıkça programlanmış kurallar gerekir. Kural motoru çok hızlıdır ama her soruyu anlayamaz; küçük dil modeli daha esnektir ama donanım ve bellek ister.

**Önerilen mimari: yerli ürün + yerel model + deterministik hızlı çekirdek.**
- MKAOS'un Türkçe ürün katmanı, araç izinleri, bellek, görev yöneticisi, güvenlik politikası, RAG, API ve Rust çıkarım altyapısı bizim kodumuz olur.
- İlk aşamada model ağırlıklarını sıfırdan eğitmek yerine, lisansı ve sabit sürümü denetlenmiş küçük bir açık ağırlıklı modeli yerelde çalıştır. Bu eğitim maliyetini ve veri toplama ihtiyacını ortadan kaldırır; modelin kökeni/lisansı yine açıkça belirtilir ve MKAOS tarafından eğitildi diye sunulmaz.
- Basit komutlar, hesaplama, durum sorgusu, şema doğrulama ve araç çağrısı LLM'ye gitmeden Rust/Python kurallarıyla çözülür. Böylece sık kullanılan işler hızlı ve tahmin edilebilir olur.
- Model yalnızca serbest dil anlama, özetleme, planlama ve kod önerisi gerektiğinde çağrılır. Uzun düşünme varsayılan değil, kullanıcı veya risk politikası isteyince açılır.
- Her model yerel diskten, sabit SHA-256 manifestiyle yüklenir. Çalışma anında indirme ve gizli bulut yedeği yoktur.

## Neden hemen sıfırdan eğitmeyelim?

Mevcut engine/mkaos-inference temel CPU tensörleri ve deneysel decoder içeriyor; üretim düzeyinde, gerçek checkpoint'lerle uyumlu tam model çalıştırıcısı değil. Ayrıca mevcut byte-tokenizer, yaygın BPE/SentencePiece modellerinin tokenizer'ıyla aynı değil. Dolayısıyla bir checkpoint'i dosya formatına dönüştürmek, mimari ve tokenizer uyumu olmadan modeli çalıştırmaya yetmez.

Rastgele ağırlıklarla sıfırdan eğitim kodu olması, anlamlı Türkçe yetenek olduğu anlamına gelmez. Küçük bir modelin bile işe yarar olması için yüksek kaliteli, lisansı açık ve eğitim/doğrulama/test ayrımları yapılmış veri; uzun eğitim ve kalite değerlendirmesi gerekir. Bu yüzden ilk hedef MKAOS'un tüm bileşenleri ve denetim katmanı bize ait, model yerel ve değiştirilebilir olmalı; kendi ağırlıklarımız ancak ölçümler ve onaylı veri hazır olduğunda ayrı bir deney olarak ele alınmalı.

## Uygulama aşamaları

### Aşama 1 — Bugün, sıfır fine-tuning
1. Operatörün cihazına Ollama veya llama.cpp kurulur ve lisansı incelenmiş küçük/quantized bir model açıkça indirilir.
2. MKAOS_OLLAMA_URL=http://127.0.0.1:11434 ve MKAOS_REPAIR_MODEL=<kurulu-model-etiketi> yalnızca CI onarım ajanı için ayarlanır.
3. Modelin yerel olduğu, indirme sonrası SHA-256'sı, quantization'ı, RAM kullanımı ve model etiketi kanıtlanır.
4. Uygulamanın normal sohbet yolu mevcut güvenli sözleşmesini korur: onaylı MKAOS checkpoint'i yoksa açık hata verir; üçüncü taraf modele sessizce geçmez. Ollama'yı ürün sohbetine bağlamak ayrı ve açık bir profil/karar olmalıdır.

### Aşama 2 — Gerçek ölçüm
- Sabit Türkçe test kümesi oluştur: komut izleme, bilgi soruları, halüsinasyon tuzakları, güvenlik reddi, JSON/araç çağrısı, uzun bağlam.
- Aynı cihazda ilk token gecikmesi, token/s, tepe RAM, cevap kalitesi ve çevrimdışı çalışma ölçülür.
- Hız hedefi donanım görülmeden vaat edilmez. Quantization RAM'i azaltabilir ama kaliteyi de etkileyebilir.
- Testleri geçmeyen model otomatik varsayılan yapılmaz.

### Aşama 3 — Gerçek MKAOS modeline geçiş
- Mevcut Rust runtime'a tokenizer uyumlu, çok katmanlı decoder, doğru attention varyantı, LM head/final norm ve gerçek artımlı KV-cache eklenir.
- Model formatı, tokenizer, mimari, lisans, kaynak revision ve SHA-256 aynı incelenmiş manifestte tutulur.
- İlk özel eğitim, yalnızca hakları ve kişisel veri durumu doğrulanmış Türkçe veriyle yapılır. Eğitim/test verisi karıştırılmaz; sonuçlar küçük bir benchmark ile karşılaştırılır.
- Bağımsız model ağırlıkları hazır olmadan MKAOS kendi LLM'si veya ChatGPT seviyesinde iddiası yapılmaz.

## Yerel CI onarım ajanı kurulumu

Bu özellik kendi kendine internete çıkıp runner kuramaz. Depo sahibi veya operatör şunları kendi yönettiği makinede yapmalıdır:
1. Güvenilir, özel erişimli bir Linux runner'ı GitHub'a self-hosted, linux, mkaos-repair etiketleriyle kaydet.
2. Docker ve Ollama kur; model ağırlıklarını önceden indir. Runner'ı ayrı, düşük ayrıcalıklı kullanıcıyla çalıştır.
3. Testlerin gerektirdiği, incelenmiş Docker imajını digest ile sabitle; MKAOS_REPAIR_SANDBOX_IMAGE değişkenine image@sha256:<64 hex> biçiminde yaz.
4. Depo Variables alanında MKAOS_REPAIR_ENABLED=true, MKAOS_REPAIR_MODEL ve MKAOS_OLLAMA_URL tanımla. İlk denemeyi ayrı test deposunda yap.
5. workflow_run tabanlı onarım workflow'u varsayılan dala birleştirildikten sonra etkinleşir. Otomatik merge ve deploy yoktur. Workflow'un dar izinleri, runner izolasyonu ve log redaksiyonu periyodik denetlenmelidir.

## Diğer gerçek entegrasyonlar için operatör kontrol listesi

- **TomTom:** API anahtarı GitHub Secret veya güvenli runtime ortamında tutulmalı; normal loglara yazılmamalı. Gerçek trafik testi için geçerli koordinat, HTTP durum kodu, kaynak ve gözlem zamanı kontrol edilmeli. Anahtar bu sohbetten/repo dosyasından paylaşılmamalı.
- **E-posta:** SMTP STARTTLS sunucusu, port, kullanıcı adı, parola, gönderen adresi ve HTTPS MKAOS_PUBLIC_BASE_URL ayarlanmalı. Doğrulama/sıfırlama mesajı gerçek test hesabına gönderilmeli; tokenlar ve SMTP parolası loglanmamalı.
- **Stripe:** Önce yalnızca sk_test_ anahtarı, test Price ID ve webhook signing secret ile Stripe test ortamı. Checkout livemode=false olmalı ve imza doğrulaması gerçek Stripe test webhook'u ile denenmeli. Canlı anahtarlar ayrı onaylı operasyon ve güvenlik incelemesi olmadan açılmamalı.
- **ML-KEM/ML-DSA:** liboqs-python ve liboqs sürümü sabitlenmeli; sağlayıcının gerçekten ML-KEM-768 ve ML-DSA-65 desteklediği doğrulanmalı. Testler anahtar üretimi, kapsülleme/çözme eşitliği, imza doğrulama ve değiştirilmiş mesajın reddini kapsamalı. Bu primitifleri üretim protokolüne bağlamadan önce uzman kriptografi incelemesi gerekir.

## Kabul kriteri

Bir özellik tamamlandı ancak gerçek sağlayıcı/yerel makinede test geçip kanıt üretirse denir. Yapılandırma örneği, mocked test veya başarılı derleme canlı entegrasyonun kanıtı değildir.