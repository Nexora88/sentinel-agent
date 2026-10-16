# MKAOS Türkçe korpus çalışma alanı

Bu dizin, lisans/izin incelemesinden geçmiş veri sürümleri için yer tutucudur. Ham korpus, kişisel veri içerebilecek dosyalar ve büyük veri arşivleri Git'e yüklenmemelidir; yerel, erişimi kısıtlı bir çalışma alanında tutulmalıdır.

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
