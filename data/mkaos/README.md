# MKAOS Türkçe korpus çalışma alanı

Bu dizin, lisans/izin incelemesinden geçmiş veri sürümleri için yer tutucudur. Ham korpus, kişisel veri içerebilecek dosyalar ve büyük veri arşivleri Git'e yüklenmemelidir; yerel, erişimi kısıtlı bir çalışma alanında tutulmalıdır.

## Common Voice Türkçe — küçük, sürümlü ilk aday

İlk aday **Common Voice Scripted Speech v27.0 — Turkish (tr)**. Mozilla Data Collective kataloğunda bu ürün CC0-1.0 olarak listeleniyor; ancak ürün kaydı veri kümesini yeniden barındırma/paylaşma yasağı da bildiriyor. Bu nedenle CC0 etiketi tek başına MKAOS model ağırlıklarını dağıtma iznini kanıtlamaz. Tam Türkçe ürün sayfası, indirme dosyası, seçilen TSV kapsamı ve ağırlık dağıtım şartları belgelenene kadar kaynak sicili kapalı kalır. [Resmî MDC kataloğu](https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk) · [Common Voice sürüm kataloğu](https://github.com/common-voice/cv-dataset).

1. Mozilla Data Collective üzerinden tam Türkçe v27.0 ürün kaydını ve koşullarını insan gözüyle doğrula. Giriş/erişim gerekirse yalnızca resmî, izinli akışı kullan.
2. Ham arşivi ve çıkarılan TSV'yi yalnızca yerel, erişimi kısıtlı dizine koy; Git'e yükleme. Ses dosyalarını bu metin-only denemeye alma.
3. Arşiv ve seçilen TSV'nin SHA-256 değerlerini yerelde kaydet; TSV'nin lisans kapsamını ve ağırlık dağıtımı koşullarını belgelemeyi tamamlamadan onay verme.
4. TSV'de `sentence` sütunu bulunan metin dosyasını seç ve ön adayları çıkar:

```bash
python tools/extract_common_voice_text.py \
  --input-tsv ./private-data/common-voice-tr-v27/validated.tsv \
  --release "Common Voice Scripted Speech v27.0 Turkish (tr)" \
  --source-uri "https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk" \
  --output-jsonl ./private-data/mkaos/cv-tr-candidates.jsonl \
  --report-json ./private-data/mkaos/cv-tr-extraction-report.json
```

Araç çevrimdışıdır; dosyanın hash'ini alır, metinleri normalize ederek yinelenenleri ayıklar, cümle gruplarını deterministik biçimde geçici train/validation/test bölmelerine ayırır ve `client_id` gibi TSV alanlarını çıktıya taşımaz. Çıktıdaki `human_review: pending`, `pii_status: unknown` ve `training_allowed: false` kasıtlıdır. Bu araç hukuki/lisans onayı veya eğitim izni vermez.

**Önemli sınırlama:** Tek bir Common Voice kaynağından gelen cümleler kaynak-bazında birbirinden ayrılamaz. Bu ön bölme yalnızca yinelenen cümle gruplarını ayırır; gerçek kaynak-disjoint değerlendirme için daha sonra bağımsız, onaylı kaynaklar ve ayrı bir Türkçe görev benchmark'ı gerekir. PII taraması da insan incelemesinin yerini tutmaz.

## İncelenmiş JSONL'den gerçek eğitim manifestine

Ön adayları otomatik olarak onaylamayın. Yetkili insan incelemesi tamamlandıktan sonra yerel bir JSONL hazırlayın; her satır şu alanları taşımalı: `sample_id`, `text`, `source_id`, `source_uri`, `document_group`, `license_id`, `consent`, `language` (`tr`), `topic`, `split`, `human_review` (`approved`) ve `pii_status` (`cleared`). `consent`, `public_domain`, `open_license` veya `not_required` değerlerinden biri olmalı. Kaynak/belge grubu bölme sızıntısı, kopyalar ve PII sinyalleri ayrıca incelenmelidir.

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
  --revision "Common Voice Scripted Speech v27.0 Turkish; local TSV SHA256: <actual-hash>" \
  --curator "<reviewing-person>"
```

`--confirm-human-license-review` yalnızca tam sürüm/dosya lisansı ve model ağırlığı dağıtım koşulları gerçekten insan tarafından incelenip belgelendiyse eklenmelidir. Bu işaret, kaynak sicili onayının yerine geçmez. Çıktılar yalnızca yeni yerel dosyalar oluşturur; mevcut dosyaların üzerine yazmaz. Gerçek SHA-256 değerini komut satırına eklemeden önce yerel rapordaki değerle karşılaştırın.

**Eğitim güvenlik kapısı:** `tools/train_mkaos_from_scratch.py` kaynak sicilini kontrol eder. Kaynak `current_approved_sources` listesinde değilse, `status: approved`, `permitted_use_now: true`, sabitlenmiş `approved_revision`, `approval_evidence` ve `weight_distribution_review: approved` alanları yoksa eğitim başlamaz. Metadata doğrulaması tek başına hukuk onayı değildir.

**Mevcut durum:** Bu depoda gerçek/onaylı Türkçe korpus bulunmuyor. Araçların varlığı veya sentetik CI verisi gerçek eğitim verisi değildir. Yerel TSV dosyası ve gerçek SHA-256 değerleri bu çalışma ortamında mevcut olmadığı için burada gerçek korpus hazırlanmış, model eğitilmiş veya checkpoint üretilmiş olarak raporlanamaz.

## Yerel ön tarama (çevrimdışı)

Ham veri yalnızca yerel ve erişimi kısıtlı bir dizinde tutulmalıdır. Kaynağın sürüm/lisans ve ağırlık dağıtım incelemesi tamamlanmadan eğitim yapmayın.

```bash
python tools/audit_mkaos_local_corpus.py \
  --input ./private-data/mkaos/reviewed-tr.jsonl \
  --report ./private-data/mkaos/local-audit.json
```

Girdi JSONL satırları en az `sample_id`, `text`, `source_id`, `source_uri`, `document_group`, `license_id`, `split`, `human_review` ve `pii_status` alanlarını içermelidir. Bu komut ağ kullanmaz; kaynak dosyanın ve her metnin hash'ini, yinelenen metinleri, yaygın PII/gizli bilgi göstergelerini ve belge grubu bölme sızıntısını raporlar. Rapor ham metinleri içermez. Bir göstergenin çıkması insan incelemesi gerektirir; hiç gösterge çıkmaması da verinin temiz olduğunu kanıtlamaz.

**Bağımsız test:** Eğitim aracı checkpoint seçimi tamamlandıktan sonra test bölümündeki byte-level kaybı bir kez ölçüp `training-report.json` içine yazar. Test kaybı checkpoint seçimi veya eğitim için kullanılmaz. Bu metrik tek başına Türkçe görev başarısı değildir; ayrıca bağımsız görev testleri ve insan değerlendirmesi gerekir.
