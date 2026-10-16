# MKAOS Türkçe korpus çalışma alanı

Bu dizin, lisans/izin incelemesinden geçmiş veri sürümleri için yer tutucudur. Ham korpus, kişisel veri içerebilecek dosyalar ve büyük veri arşivleri Git'e yüklenmemelidir; yerel, erişimi kısıtlı bir çalışma alanında tutulmalıdır.

## Common Voice Türkçe — küçük, sürümlü ilk aday

İlk aday olarak **Common Voice Scripted Speech v27.0 — Turkish (tr)** hedefleniyor. Common Voice sürüm kataloğu v27.0'ı Eylül 2026 sürümü olarak listeliyor; bu, Türkçe ürün sayfasının lisansını, belirli TSV dosyasını veya model ağırlıklarını dağıtma hakkını tek başına doğrulamaz. Kaynak sicili bu nedenle kapalı kalır.

1. Mozilla Data Collective üzerinden tam olarak Türkçe v27.0 ürün sayfasını ve şartlarını insan gözüyle doğrula. Giriş/erişim gerekirse yalnızca resmî, izinli akışı kullan.
2. Ham arşivi ve çıkarılan TSV'yi yalnızca yerel, erişimi kısıtlı dizine koy; Git'e yükleme. Ses dosyalarını bu metin-only denemeye alma.
3. Arşiv ve seçilen TSV'nin SHA-256 değerlerini yerelde kaydet; TSV'nin lisans kapsamını ve ağırlık dağıtımı koşullarını belgelemeyi tamamlamadan onay verme.
4. TSV'de `sentence` sütunu bulunan metin dosyasını seç ve ön adayları çıkar:

```bash
python tools/extract_common_voice_text.py \
  --input-tsv ./private-data/common-voice-tr-v27/validated.tsv \
  --release "Common Voice Scripted Speech v27.0 Turkish (tr)" \
  --source-uri "https://commonvoice.mozilla.org/datasets" \
  --output-jsonl ./private-data/mkaos/cv-tr-candidates.jsonl \
  --report-json ./private-data/mkaos/cv-tr-extraction-report.json
```

`--source-uri` alanını mümkünse doğruladığın tam Türkçe ürün sayfasıyla değiştir. Araç çevrimdışıdır; dosyanın hash'ini alır, metinleri normalize ederek yinelenenleri ayıklar, cümle gruplarını deterministik biçimde geçici train/validation/test bölmelerine ayırır ve `client_id` gibi TSV alanlarını çıktıya taşımaz. Çıktıdaki `human_review: pending`, `pii_status: unknown` ve `training_allowed: false` kasıtlıdır. Bu araç hukuki/lisans onayı veya eğitim izni vermez.

**Önemli sınırlama:** Tek bir Common Voice kaynağından gelen cümleler kaynak-bazında birbirinden ayrılamaz. Bu ön bölme yalnızca yinelenen cümle gruplarını ayırır; gerçek kaynak-disjoint değerlendirme için daha sonra bağımsız, onaylı kaynaklar ve ayrı bir Türkçe görev benchmark'ı gerekir. PII taraması da insan incelemesinin yerini tutmaz.

## Dosya akışı

1. Kaynak sicilindeki kaynağı ve **belirli sürümünü** incele.
2. Lisans, atıf, izin, gizlilik ve ağırlık dağıtım koşulları belgelenmeden veriyi kabul etme.
3. Onaylı Türkçe talimat/yanıt örneklerini UTF-8 JSONL olarak hazırla. Her örnek `source_id`, `source_uri`, `license_id`, `consent: true` ve `review_status: "approved"` alanlarını taşımalıdır.
4. `source_id` değerini veri kümesi adına değil, bölme sızıntısını önlemek için mümkün olduğunca kaynak/doküman grubu düzeyinde ver.
5. Bölme manifestini yerel olarak üret; raporu gözden geçir ve bağımsız test bölümünü kilitle.
6. Eğitim başlamadan önce manifest ve veri dosyalarının SHA-256 değerlerini kaydet.

Örnek komut (yerel dosya yollarını kendi onaylı veri dizinine göre değiştir):

```bash
python -m tools.prepare_mkaos_training_dataset \
  --input ./private-data/reviewed-tr.jsonl \
  --output ./artifacts/mkaos-training-manifest.json \
  --report ./artifacts/mkaos-training-report.json \
  --min-examples-per-split 100
```

Komut ağ kullanmaz ve ağırlık eğitmez. Kaynak grubu bazlı bölme nedeniyle az sayıda kaynağın bulunduğu küçük veri kümesi bölme eşiğini geçemeyebilir; bu durumda kaynakları satır bazında karıştırarak sızıntı yaratma. Daha fazla bağımsız, onaylı kaynak ekle.

**Eğitim güvenlik kapısı:** `tools/train_mkaos_from_scratch.py` artık `data/mkaos/source-register.json` dosyasını da kontrol eder. Kaynak `current_approved_sources` listesinde değilse, `status: approved`, `permitted_use_now: true`, sabitlenmiş `approved_revision`, `approval_evidence` ve `weight_distribution_review: approved` alanları yoksa eğitim başlamaz. Metadata doğrulaması tek başına hukuk onayı değildir.

**Mevcut durum:** Bu depoda gerçek/onaylı Türkçe korpus bulunmuyor. Yer tutucu README, örnek kayıt veya CI testi gerçek eğitim verisi değildir.

## Yerel ön tarama (çevrimdışı)

Ham veri yalnızca yerel ve erişimi kısıtlı bir dizinde tutulmalıdır. Kaynağın sürüm/lisans ve ağırlık dağıtım incelemesi tamamlanmadan eğitim yapmayın.

```bash
python tools/audit_mkaos_local_corpus.py \
  --input ./private-data/reviewed-tr.jsonl \
  --report ./artifacts/mkaos-local-audit.json
```

Girdi JSONL satırları en az `sample_id`, `text`, `source_id`, `source_uri`, `document_group`, `license_id`, `split`, `human_review` ve `pii_status` alanlarını içermelidir. Bu komut ağ kullanmaz; kaynak dosyanın ve her metnin hash'ini, yinelenen metinleri, yaygın PII/gizli bilgi göstergelerini ve belge grubu bölme sızıntısını raporlar. Rapor ham metinleri içermez. Bir göstergenin çıkması insan incelemesi gerektirir; hiç gösterge çıkmaması da verinin temiz olduğunu kanıtlamaz.

**Bağımsız test:** Eğitim aracı artık checkpoint seçimi tamamlandıktan sonra test bölümündeki byte-level kaybı bir kez ölçüp `training-report.json` içine yazar. Test kaybı checkpoint seçimi veya eğitim için kullanılmaz. Bu metrik tek başına Türkçe görev başarısı değildir; ayrıca bağımsız görev testleri ve insan değerlendirmesi gerekir.
