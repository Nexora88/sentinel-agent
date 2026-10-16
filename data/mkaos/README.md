# MKAOS Türkçe korpus çalışma alanı

Ham veri, kişisel veri içerebilecek dosyalar ve büyük arşivler Git'e yüklenmemelidir; yerel ve erişimi kısıtlı bir çalışma alanında tutulmalıdır. Bu depoda şu an gerçek yerel arşiv/TSV, gerçek korpus hash'i veya eğitim checkpoint'i bulunmuyor.

## Sabitlenen ilk aday: Common Voice Scripted Speech 27.0 Turkish

- Resmî ürün kaydı: https://mozilladatacollective.com/datasets/cmu5wkah500c2o10719lem8m8
- Dataset ID: `cmu5wkah500c2o10719lem8m8`
- Sürüm: `cv-corpus-27.0-2026-09-11`; ürün sayfası yayın tarihi 17 Eylül 2026.
- Ürün sayfası lisansı: CC0-1.0; sayfa ayrıca veri kümesini yeniden barındırmayı/paylaşmayı yasaklıyor.
- Datasheet kaynak dökümü: yaklaşık %85.0 Türkçe Wikipedia, %11.6 sentence-collector, %1.2 SETimes, %2.2 Other.
- Yalnızca metin denemesi için seçilecek dosya: `validated_sentences.tsv`; ses ve konuşmacı alanları kullanılmamalı.

**Lisans kapısı hâlâ kapalı.** Ürün sayfasının CC0 bildirimi önemli bir kanıttır, ancak kaynak dökümündeki Wikipedia/SETimes/diğer kökenler ve MKAOS gibi genel amaçlı üretken dil modeli ağırlıklarının dağıtımı için kaynak kapsamı ayrıca incelenmelidir. Kaynak sicilinde Common Voice hâlâ onaysızdır. Dosya SHA-256 değerleri yerel dosya edinilmeden üretilemez ve uydurulamaz. Mozilla ayrıca dataset'i yeniden barındırmamayı istiyor; ham arşivi veya metin dosyasını GitHub'a, issue'lara, loglara ya da bu raporlara koymayın.

1. Mozilla Data Collective üzerinde tam ürün kaydını açıp izin verilen erişim akışıyla indirme yap. Erişim gereksinimlerini aşmaya çalışma.
2. İndirilen arşivi ve seçilen TSV'yi yerel, erişimi kısıtlı klasörde tut. Sadece bu iki dosyanın SHA-256 değerlerini özel yerel kayda yaz.
3. Arşivde `validated_sentences.tsv` varsa yalnızca o dosyayı seç. TSV'de `sentence` ve `source` sütunlarının ikisi de bulunmalıdır.
4. Kaynak etiketlerini ve olası üst kaynak lisanslarını insan incelemesine gönder; otomatik script bu kararı veremez.
5. Aday metni çıkar:

```bash
python tools/extract_common_voice_text.py \
  --input-tsv ./private-data/common-voice-tr-v27/validated_sentences.tsv \
  --release "Common Voice Scripted Speech 27.0 Turkish; cv-corpus-27.0-2026-09-11" \
  --source-uri "https://mozilladatacollective.com/datasets/cmu5wkah500c2o10719lem8m8" \
  --output-jsonl ./private-data/mkaos/cv-tr-candidates.jsonl \
  --report-json ./private-data/mkaos/cv-tr-extraction-report.json
```

Çıkarıcı çevrimdışıdır. Dosyanın gerçek hash'ini raporlar, normalize edilmiş kopyaları ayıklar, kaynak etiketlerini saklar ve kaynak etiketine göre deterministik bölme yapar. `license_id: unreviewed`, `human_review: pending`, `pii_status: unknown` ve `training_allowed: false` bilerek kullanılır. Kaynak etiketleri lisans değildir. Bir metin birden fazla kaynakta görünüyorsa bu satır manuel incelenmelidir. Kaynak düzeyinde ayırma üç bölmeyi doldurmazsa bölmeleri rastgele karıştırmayın; bağımsız, izinli kaynak ekleyin.

## Yerel hash'leri doğrulama

Linux/macOS:

```bash
sha256sum ./private-data/common-voice-tr-v27/common-voice-scripted-speech-27-0-turkis-b14760fe.tar.gz
sha256sum ./private-data/common-voice-tr-v27/validated_sentences.tsv
```

Windows PowerShell:

```powershell
Get-FileHash .\private-data\common-voice-tr-v27\common-voice-scripted-speech-27-0-turkis-b14760fe.tar.gz -Algorithm SHA256
Get-FileHash .\private-data\common-voice-tr-v27\validated_sentences.tsv -Algorithm SHA256
```

Dosya adını indirdiğin gerçek dosyaya göre düzelt. Hash'leri herkese açık PR'a yazmak zorunlu değildir; yerel audit manifestinde ve kaynak onay kaydında saklanabilir. Bu araç ortamında arşiv/TSV olmadığı için gerçek hash değerleri üretilmedi.

## Kişisel veri, kopya ve bölme denetimi

Ham TSV'den çıkan kayıtlar doğrudan eğitime verilemez. Her kayıt için doğru kaynak kimliği, kaynak URI, lisans/izin, belge grubu, konu, `human_review=approved` ve `pii_status=cleared` alanları insan incelemesiyle doldurulmalıdır. Kaynaklar ve belge grupları farklı bölmelere sızmamalı; çok kaynaklı kopyalar karara bağlanmalıdır.

```bash
python tools/audit_mkaos_local_corpus.py \
  --input ./private-data/mkaos/reviewed-tr.jsonl \
  --report ./private-data/mkaos/local-audit.json

python tools/build_mkaos_training_manifest.py \
  --input ./private-data/mkaos/reviewed-tr.jsonl \
  --corpus-output ./private-data/mkaos/trainer-corpus.jsonl \
  --manifest-output ./private-data/mkaos/training-manifest.json \
  --report-output ./private-data/mkaos/manifest-report.json \
  --dataset-id "mkaos-tr-reviewed" \
  --revision "cv-corpus-27.0-2026-09-11; TSV SHA256 recorded in local audit" \
  --curator "<reviewing-person>"
```

`--confirm-human-license-review` yalnızca tam sürüm, seçilen dosya, köken kaynakları ve model ağırlığı dağıtımı gerçekten insan/hukuk incelemesinden geçip kanıtı kaydedildiyse eklenmelidir. Bu seçenek bile kaynak sicilinin yerini tutmaz. Çıktılar mevcut dosyaların üzerine yazmaz.

## Rastgele başlangıçtan eğitim

Eğitim kapısı şu an kapalıdır. Kaynak sicilinde `current_approved_sources` boş ve `model_training_allowed: false`. Lisans/köken/ağırlık dağıtımı kanıtları ve yerel hash'ler olmadan bunları değiştirmeyin. Kapı onaylandıktan sonra, eğitim cihazında PyTorch kurulu olmak üzere:

```bash
python tools/validate_mkaos_training_manifest.py ./private-data/mkaos/training-manifest.json
python tools/train_mkaos_from_scratch.py \
  --corpus ./private-data/mkaos/trainer-corpus.jsonl \
  --manifest ./private-data/mkaos/training-manifest.json \
  --output-dir ./private-data/mkaos/run-001
```

Bu model byte-token tabanlı küçük deneysel bir mimaridir; büyük model performansı beklenmemeli. Test kaybı checkpoint seçimi bittikten sonra bir kez ölçülür ve model seçimi için kullanılmaz.

## Rust checkpoint doğrulaması ve bağımsız Türkçe görevler\n\nİnsan değerlendirme rubriği ve test tasarımı: `docs/MKAOS_HUMAN_EVALUATION_PROTOCOL.md`.

Rust crate içindeki checkpoint loader, SHA-256, dosya yapısı, tensor boyutları ve sonlu ağırlıkları doğrulayabilir; bunun başarılı olması tek başına checkpoint'in model mimarisiyle uyumlu üretim çıkarımı yaptığı anlamına gelmez. Gerçek eğitim checkpoint'i yokken gerçek checkpoint yükleme testi raporlanamaz.

Bağımsız Türkçe görev değerlendirmesi için izinli, insan tarafından gözden geçirilmiş ve eğitim/validasyon kaynaklarından ayrı test soruları hazırlanmalıdır. Test cevapları model seçimi sırasında gösterilmemelidir. Rust motorunun tam olarak hangi checkpoint hash'ini ve hangi decode ayarlarını kullandığı kaydedilmelidir. Tahminleri aldıktan sonra:

```bash
python tools/evaluate_mkaos_turkish_tasks.py \
  --input ./private-data/mkaos/independent-test-predictions.jsonl \
  --checkpoint-sha256 "<actual-checkpoint-sha256>" \
  --output ./private-data/mkaos/independent-test-report.json
```

Her satır `case_id`, `task`, `prompt`, `reference`, `prediction`, `source_id`, `document_group`, `human_review=approved`, `split=test` ve mümkünse insan puanı (`human_score` 0-4) içermelidir. Bu araç değerlendirme verisini rapora yazmaz, yalnızca ölçüm özetini üretir. Exact-match tek başına açık uçlu Türkçe kalitesini ölçmez.

## Hash kayıt aracını kullanma

Arşiv ve TSV gerçekten yerel olarak edinildikten sonra hash'leri otomatik kaydetmek için:

```bash
python tools/record_mkaos_local_artifact_hashes.py \
  --archive ./private-data/common-voice-tr-v27/<gercek-arsiv-dosyasi> \
  --tsv ./private-data/common-voice-tr-v27/validated_sentences.tsv \
  --output ./private-data/mkaos/local-artifact-hashes.json
```

Araç dosyaların gerçek baytlarını okur, SHA-256 ve boyutları kaydeder; dosyaları yüklemez ve mevcut raporun üzerine yazmaz. Hash kaydı lisans izni veya eğitim onayı değildir. Bu JSON yerel/özel tutulmalı; Git'e ham veri veya kişisel veri koyulmamalıdır.

## Gerçek durum

- Resmî Common Voice Türkçe v27.0 ürün sayfası ve dataset ID sabitlendi.
- Yerel arşiv ve TSV bu çalışma ortamında mevcut değil; gerçek dosya hash'leri yok.
- Kaynak/lisans/mahremiyet/ağırlık dağıtımı onayı verilmedi.
- Gerçek eğitim ve checkpoint üretimi yapılmadı.
- Rust motorunda gerçek checkpoint yüklemesi ve bağımsız görev testleri henüz doğrulanmadı.
- Eğitim kapısı kapalı kalıyor.
