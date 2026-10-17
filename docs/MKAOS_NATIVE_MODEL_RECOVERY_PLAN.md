# MKAOS Yerli Model Kurtarma ve Eğitim Planı

**Durum (2026-10-17):** MKAOS'un kendi Rust çıkarım motoru ve rastgele başlatılmış ağırlıklarla eğitim aracı var; ancak onaylı Türkçe korpus, eğitilmiş kullanılabilir MKAOS checkpoint'i ve bağımsız kalite sonucu henüz yok. Yarım milyon kayıt sayısı tek başına eğitim başarısını, veri kalitesini veya donanım yeterliliğini kanıtlamaz. Bu belge tamamlanmış eğitim iddiası değildir; ölçülebilir kurtarma planıdır.

## Karar

MKAOS, Ollama'yı zorunlu çalışma zamanı yapmayacak ve üçüncü taraf model ağırlıklarına sessiz geri dönüş yapmayacak. Kendi tokenizer sözleşmesi, veri hattı, eğitim döngüsü, checkpoint biçimi, Rust çıkarım motoru ve değerlendirme seti geliştirilecek. Bununla birlikte, önceden eğitilmiş yabancı ağırlık olmadan sıfırdan genel amaçlı güçlü bir LLM üretmek küçük bir GPU makinesinde yüz binlerce belgeyle garanti edilemez. İlk hedef genel zekâ değil, dar kapsamlı ve ölçülebilir Türkçe kod/savunmacı siber güvenlik asistanıdır.

## Aşamalar ve geçiş kapıları

### 0. Çakılmanın nedenini teşhis et
- Her koşuda Python/PyTorch/CUDA sürümü, GPU/VRAM, sistem RAM'i, model boyutları, batch, sequence length, precision, optimizer, token sayısı, adım/saniye, tepe VRAM/RAM ve tam hata izi raporlansın.
- OOM, sürücü uyumsuzluğu, bozuk veri/manifest, NaN/Inf, tokenizer/sequence maliyeti ve uzun epoch durumları birbirinden ayrılsın.
- Başarısız koşu aynı ayarlarla körlemesine tekrarlanmasın. Önce küçük sentetik veriyle eğitim adımı, checkpoint kaydetme-yükleme ve devam etme doğrulansın.
- Kabul: hata sınıfı tekrarlanabilir biçimde belirlenmiş, kaynak kullanımı kaydedilmiş ve küçük test koşusu tamamlanmış olmalı.

### 1. Veri setini sayımdan kaliteye taşı
- 500.000 kayıt yerine benzersiz temizlenmiş token sayısı ve belge uzunluğu dağılımı raporlansın.
- Kaynak, lisans/izin, tarih, SHA-256, kişisel veri kontrolü, insan incelemesi ve split her örneğe bağlansın. Yetkisiz, gizli anahtar içeren veya gereksiz kişisel veri taşıyan kayıtlar çıkarılsın.
- Yakın kopyalar ve veri sızıntısı tespit edilsin; train/validation/test ayrımı eğitimden önce sabitlensin. Test verisi eğitime veya hiperparametre seçimine karışmasın.
- Kabul: mevcut manifest doğrulayıcısından geçen, insan onaylı ve lisansı izlenebilir korpus ve ayrı held-out test seti.

### 2. Gerçek donanıma göre küçük başlangıç modeli
- Önce 10M–30M parametre aralığında altyapı denemesi yapılsın; bunun iyi bir sohbet modeli olacağı iddia edilmesin. Eğitim hattı doğrulanınca 50M–135M deneylerine geçilsin.
- 135M–350M hedefi otomatik varsayılmasın. Eğitim aracındaki bellek tahmini gerçek tepe ölçümleriyle karşılaştırılsın; optimizer durumları, gradyanlar, aktivasyonlar ve CUDA workspace maliyeti hesaba katılsın.
- Kısa sequence ve küçük batch ile başlansın; cihaz destekliyorsa gradient accumulation, mixed precision, activation checkpointing ve verimli attention aşamalı test edilsin. NaN kontrolleri eklensin.
- Her koşu seed, config, git commit, veri manifest hash'i ve tokenizer sürümüyle yeniden üretilebilir olmalı. Checkpoint kaydetme, geri alma ve kesintiden devam test edilmeli.
- Kabul: eğitim/validation loss eğrisi, örnek üretim, kaydet-yükle ve yeniden başlatma testleri. Yalnızca sürecin bitmesi yeterli değildir.

### 3. Tokenizer ve dil yeteneği
- Mevcut mkaos-byte-v1 tokenizer 257 token'lı byte tabanlı sözleşmedir; basit ve uyumludur ancak Türkçe metinde token dizilerini uzatabilir. Büyük ölçekli eğitim öncesinde sürümlü, test vektörlü ve geri uyum planlı Türkçe-dostu tokenizer değerlendirilsin.
- Tokenizer checkpoint ile birlikte sürümlenmeli; eğitim ve çıkarımda aynı tokenizer kullanılmalı.
- İlk görevler Türkçe teknik talimatı anlama, kod açıklama, statik kod inceleme, savunmacı güvenlik bulgularını gerekçelendirme ve kaynak/kanıt gösterme olmalı.

### 4. Bağımsız değerlendirme
- Sabit Türkçe held-out test seti ve insan puanlaması oluşturulsun: doğruluk, talimata uyum, kod değerlendirmesi, halüsinasyon, güvenlik, Türkçe kalitesi ve gecikme.
- Aynı prompt, donanım ve ölçüm koşullarıyla sürümler karşılaştırılsın. Harici model yalnızca isteğe bağlı kıyas noktası olabilir; zorunlu runtime olamaz.
- Bağımsız test kapısı geçilmeden yerli model başarılı, üretime hazır veya egemenlik kanıtlandı iddiaları kullanılmasın.

### 5. Dağıtık eğitim daha sonraki araştırma
- agent_mesh altyapısının varlığı, dağıtık eğitim altyapısının hazır olduğu anlamına gelmez. Farklı ev bilgisayarlarını tek GPU gibi birleştirmek kolay değildir; gecikme, bant genişliği, arıza toleransı ve gradient senkronizasyonu temel zorluklardır.
- Önce tek makinede tekrarlanabilir eğitim, sonra kontrollü iki makineli deney ve ölçümlü iletişim/yeniden başlatma testi yapılmalı. P2P eğitim ancak tehdit modeli, düğüm kimliği, mTLS, imzalı iş tanımı, veri minimizasyonu ve bozuk gradyan savunması tasarlandıktan sonra ele alınmalı.
- Gönüllü düğümlere ham özel korpus dağıtılmamalı. Federated learning kendiliğinden verinin dışarı çıkmadığını garanti etmez.

## Her deney için zorunlu kayıt
- Git commit ve eğitim config'i; korpus/manifest/tokenizer SHA-256 ve lisans durumu.
- Parametre ve token sayısı, batch, sequence length, precision, optimizer.
- Donanım/sürücü, tepe RAM/VRAM, adım/saniye, toplam süre.
- Train/validation loss, NaN/Inf sayısı, checkpoint hash'i ve sabit test kümesi sonuçları.
- Örnek hatalar, insan değerlendirmesi, ağ erişimi ve harici servislere yapılan çağrıların kaydı.

## Faz 1 — yerel tanılama aracını çalıştırma

Yeni araç `tools/diagnose_mkaos_training.py` ağ kullanmadan şu ölçümleri üretir:
- Python, PyTorch, CUDA/ROCm görünürlüğü, GPU adı/toplam ve boş VRAM (PyTorch destekliyorsa), sistem RAM'i ve CPU çekirdek sayısı.
- Verilen model yapılandırmasının parametre ve yaklaşık eğitim belleği hesabı.
- İsteğe bağlı JSONL korpus için yerel okuma/JSON parse, UTF-8 byte-token sayımı ve saniyedeki token hızı.
- Gerçek checkpoint ve yerel `mkaos-generate` ikilisi sağlanırsa tek tokenlık üretimin soğuk süreç duvar saati gecikmesi. Bu ölçüm süreç açılışı ve model yüklemesini de içerir; sıcak, süreç içi TTFT değildir.

Önce donanım ve varsayılan küçük yapılandırmayı ölç:

```bash
python tools/diagnose_mkaos_training.py
```

Korpus hızını ölçmek için (dosya yalnızca yerel okunur):

```bash
python tools/diagnose_mkaos_training.py --corpus /yerel/yol/corpus.jsonl
```

Eğitimde kullanılan yapılandırmaya yaklaşmak için gerçek değerleri açıkça geçir:

```bash
python tools/diagnose_mkaos_training.py --corpus /yerel/yol/corpus.jsonl --hidden-size 64 --layers 2 --heads 4 --kv-heads 2 --intermediate-size 128 --batch-size 8 --sequence-length 128
```

Yerel Rust CLI ve checkpoint hazırsa TTFT ölçümü:

```bash
python tools/diagnose_mkaos_training.py --native-cli ./engine/mkaos-inference/target/release/mkaos-generate --checkpoint /yerel/yol/model.mkaosw --heads 4 --kv-heads 2 --sequence-length 128
```

Bu araç **eğitimi başlatmaz, ayar değiştirmez, dosya yüklemez ve veri göndermez**. Bellek tahmini yaklaşık değerdir. Korpus hızı, eğitim adımı hızının yerine geçmez. Gerçek hata nedenini saptamak için başarısız koşunun tam traceback'i ve aynı koşudaki kaynak ölçümleri gereklidir.

## İlk uygulanacak işler
1. Tanılama aracını eğitim çökmesinin yaşandığı aynı PC ve Python ortamında çalıştır; JSON çıktısını sakla.
2. Son başarısız eğitim koşusunun tam hata izini ve o koşuda kullanılan tüm parametreleri al.
3. Eğitim aracına dry-run/bellek tahmini ve küçük sentetik smoke test ekle.
4. Resume/checkpoint ve ölçüm kayıtlarını doğrula.
5. Korpus manifestini ve split'leri doğrula; veri kalitesi raporu çıkar.
6. Küçük modelde uçtan uca eğitim ve Rust checkpoint round-trip tamamla.
7. Bundan sonra model boyutunu artır ve gerçek Türkçe değerlendirmeye geç.

**Önemli:** Bu plan kodda bütün özelliklerin tamamlandığı anlamına gelmez. Her madde ayrı commit, test ve ölçümle kapatılmalıdır. Donanım raporu ve başarısız log olmadan kesin çökme nedeni söylenemez.