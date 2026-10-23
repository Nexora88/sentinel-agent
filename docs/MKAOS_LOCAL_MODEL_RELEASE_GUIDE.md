# MKAOS yerel model: tekrarlanabilir eğitim, çıkarım ve Türkçe değerlendirme

Bu belge uygulanabilir komutları ve üretim kabul kapılarını bir araya getirir. **Komutların ve testlerin depoda bulunması, gerçek eğitim veya bağımsız kalite değerlendirmesinin yapıldığı anlamına gelmez.** Eğitim şu anda yalnızca kaynak kaydı ve onaylı manifest kapılarını geçen yerel veriyle yapılabilir.

## 0. Şu anki dürüst durum

- data/mkaos/source-register.json içinde onaylı eğitim kaynağı bulunmadığı sürece üretim eğitimi **BLOCKED** kalmalıdır.
- tools/train_mkaos_profile.py gerçek eğitimi başlatır; korpus/manifest indirmez ve hak incelemesinin yerine geçmez.
- Rust mkaos-run / mkaos-generate, MKAOSW1 byte-tokenizer checkpoint sözleşmesini doğrulayabilir. Bu, başka model mimarilerinin (ör. BPE/GQA farklılıkları) uyumlu olduğu anlamına gelmez.
- Genel amaçlı kullanıma hazır, bağımsız Türkçe kalite skoru veya gerçek hedef cihaz ölçümü ancak çıktı artefaktları ve bağımsız inceleme ile kanıtlanabilir.

## 1. Ortamı hazırlama

Python 3.12 ve Rust toolchain kurulu bir Linux makinede, projeyi sabit bir commit'e checkout edin. Eğitim için ayrı bir sanal ortam kullanın; üretim sırlarını eğitim ortamına koymayın.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch
cargo test --manifest-path engine/mkaos-inference/Cargo.toml
python -m unittest discover -s tests -v
```

Windows veya farklı GPU sürücülerinde komut/bağımlılıklar değişebilir. CI kotası doluysa bu, testlerin geçtiği anlamına gelmez; aynı komutlar yetkili yerel ortamda çalıştırılmalı ve günlükleri saklanmalıdır.

## 2. Veri onayı ve tekrarlanabilir eğitim

1. Veri sahibi, lisans/atıf, kişisel veri, gizli bilgi, saklama ve model-ağırlığı dağıtım haklarını inceler.
2. Yalnızca onaylanan örnekler yerel JSONL dosyasında tutulur. Ham veri, özel örnekler veya kimlik bilgileri Git'e eklenmez.
3. Kaynak bazında train/validation/test ayrımını ve içerik hash'lerini içeren manifest oluşturulur. Test bölümü eğitim ve ayar seçimi sırasında kullanılmaz.
4. Kaynak kaydı, manifest doğrulaması ve donanım/bellek ön kontrolü geçmeden eğitimi zorlamayın.

Önce veri yönetişimi:

```bash
python tools/prepare_mkaos_training_dataset.py \
  --input /secure/local/mkaos-approved.jsonl \
  --output /secure/local/mkaos-manifest.json \
  --report /secure/local/mkaos-data-audit.json \
  --min-examples-per-split 2
```

Ardından profildeki mimari/parametre sayısı doğrulanarak eğitim:

```bash
python tools/train_mkaos_profile.py \
  --profile configs/mkaos/train-135m.json \
  --corpus /secure/local/mkaos-approved-corpus.jsonl \
  --manifest /secure/local/mkaos-manifest.json \
  --output-dir /secure/local/artifacts/mkaos-run-001 \
  --device auto
```

Yollar örnektir; dosyaların gerçekten mevcut ve onaylı olması gerekir. Yerel sahip verisi için --experimental-local-only yalnızca açık bir yerel deneme seçeneğidir; üçüncü taraf haklarını onaylamaz ve checkpoint dağıtım izni vermez. Tohum, git commit'i, komut, PyTorch/Rust sürümü, donanım, manifest hash'i, eğitim/validation eğrisi ve checkpoint hash'i sonuç raporunda saklanmalıdır. Aynı koşullar aynı sonucu vermiyorsa farkı açıklamadan "tekrarlanabilir" demeyin.

## 3. SHA-256 doğrulaması ve gerçek yerel çıkarım

Eğitim çıktısındaki gerçek checkpoint hash'ini alın; hash'i tahmin etmeyin veya dosya adından çıkarmayın:

```bash
sha256sum /secure/local/artifacts/mkaos-run-001/mkaos-owned.mkaosw
```

Checkpoint mimarisiyle uyumlu başlık/KV başlığı ve dizi uzunluğunu eğitim raporundan kullanarak yerel CLI'ı derleyin:

```bash
cargo build --release --manifest-path engine/mkaos-inference/Cargo.toml
./engine/mkaos-inference/target/release/mkaos-run \
  --checkpoint /secure/local/artifacts/mkaos-run-001/mkaos-owned.mkaosw \
  --sha256 <GERCEK_SHA256> \
  --heads <HEADS> --kv-heads <KV_HEADS> \
  --max-seq-len <MAX_SEQ> --max-new-tokens 48 \
  --prompt "Türkiye'nin başkenti neresidir?"
```

Komutun başarılı çıkması yalnızca checkpoint'in mevcut Rust sözleşmesine göre yüklenip çıkarım yapabildiğini kanıtlar. Modelin doğru Türkçe ürettiğini kanıtlamaz. Hash uyuşmazlığını, mimari/şekil uyuşmazlığını veya UTF-8 çözümleme hatasını görmezden gelmeyin.

Çevrimdışı kabul için model ve bağımlılıkları önceden sağlayın, sonra çıkarım sürecinin ağ çıkışını işletim sistemi/konteyner düzeyinde kapatın. Sadece bir çevre değişkeni ayarlamak çevrimdışı çalışmayı kanıtlamaz.

## 4. Sabit Türkçe test kümesi ve değerlendirme

benchmarks/mkaos-general-llm-tr-001.json başlangıç regresyon kümesidir; tek başına bağımsız/istatistiksel olarak temsili benchmark değildir. Aynı sabit prompt'ları, üretim ayarlarını ve donanımı tüm modellerde kullanın. Cevapları şu JSONL biçiminde kaydedin:

```json
{"case_id":"gk-capital-001","answer":"...","latency_ms":123.4,"peak_memory_mb":512}
```

Makine tarafından üretilen duman testi raporu:

```bash
python tools/evaluate_mkaos_answers.py \
  --dataset benchmarks/mkaos-general-llm-tr-001.json \
  --answers /secure/local/artifacts/mkaos-answers.jsonl \
  --output /secure/local/artifacts/mkaos-evaluation.json
```

Bu araç terim eşleşmesi, eksik/fazla örnek, tekrar, verilen gecikme ve bellek değerlerini raporlar; **doğruluk veya akıcılık için otomatik hakem değildir**. Her çıktı bağımsız değerlendiriciler tarafından, model kimliği mümkün olduğunca gizlenerek şu ayrı eksenlerde puanlanmalıdır:

- Olgusal doğruluk ve kanıt/kaynak kullanımı
- Türkçe dilbilgisi, doğallık, anlaşılabilirlik
- Talimata uyum ve muhakeme
- Güvenlik, uygun ret ve prompt-injection dayanıklılığı
- Belirsizliği dürüstçe ifade etme ve uydurma oranı
- Gecikme, üretilen token/s, soğuk başlama, RAM ve varsa VRAM

Eşikler test sonuçları görülmeden belirlenmeli; en az iki insan değerlendirici örnek bir alt kümede bağımsız puanlama yapmalı, anlaşmazlıklar kaydedilmelidir. Güvenlik testleri tehlikeli talimatların ayrıntılı örneklerini yayımlamadan kategori ve sonuç düzeyinde raporlanabilir. Held-out test setini model ayarı için kullanmayın. Ölçüm raporuna veri kümesi hash'i, checkpoint/tokenizer hash'i, git commit'i, donanım, runtime sürümü, yöntem, örnek sayısı, eksik cevaplar ve sınırlamalar ekleyin.

Hedef makinede soğuk/sıcak gecikme ve kaynak kullanımı için:

```bash
python tools/benchmark_mkaos_device.py --help
```

Bu betik gerçek sunucu/endpoint gerektirir. Mevcut Rust CLI tekil çıkarım için uygundur; token akışı zaman damgaları olmadan tam yanıt süresini TTFT diye raporlamayın.

## 5. İnsanların güvenle kullanabilmesi için yayın kapısı

Bir checkpoint genel kullanıcıya varsayılan olarak sunulmadan önce hepsi doğrulanmalı:

- [ ] Veri ve checkpoint lisans/provenans onayı; dağıtım hakkı ayrıca karara bağlandı
- [ ] Aynı commit/manifest/seed/konfigürasyonla yeniden üretim denemesi
- [ ] Checkpoint ve tokenizer SHA-256 manifesti temiz ortamda doğrulandı
- [ ] Gerçek hedef Rust runtime'ında çıkarım ve hash uyuşmazlığı negatif testi
- [ ] Ağ çıkışı kapalıyken çıkarım testi
- [ ] Bağımsız Türkçe kalite ve güvenlik incelemesi; kategori bazlı sonuçlar
- [ ] Gerçek donanımda gecikme/RAM/VRAM ve soğuk başlangıç raporu
- [ ] Geri alma planı, sürüm notları, model kartı, bilinen sınırlar ve güvenli varsayılanlar
- [ ] Uygulama arayüzünde modelin yerel/çevrimdışı durumu ve deneysel statüsü doğru gösteriliyor

Bir kapı BLOCKED veya NOT RUN ise model üretime hazır ilan edilmemelidir. Küçük byte-level modelin eğitilmiş olması tek başına güçlü genel amaçlı asistan olacağı anlamına gelmez. Önce gerçek veri, eğitim, mimari uyumu ve bağımsız kalite kanıtı gerekir.
