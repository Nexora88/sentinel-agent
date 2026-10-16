# MKAOS düşük bellekli eğitim denemeleri

Bu belge, eğitim altyapısındaki bellek ve optimizasyon seçeneklerini açıklar. Gerçek korpus ve kaynak onayı olmadan eğitim başlatmak için izin değildir.

## Mikro-batch ve gradient accumulation

Eğitim komutuna şu seçenekler eklendi:

- `--batch-size`: GPU/CPU belleğine sığacak mikro-batch boyutu.
- `--gradient-accumulation-steps`: ağırlık güncellemesinden önce kaç mikro-batch gradyanının biriktirileceği. Yaklaşık etkin batch boyutu iki değerin çarpımıdır. Aktivasyon belleğini azaltmaya yardımcı olur; tek başına daha hızlı eğitim garantisi değildir.
- `--warmup-steps`: başlangıç öğrenme oranını doğrusal biçimde artıran optimizer adımı sayısı; varsayılan 0.
- `--min-learning-rate-ratio`: kosinüs azalışının taban öğrenme oranı / başlangıç öğrenme oranı oranı; varsayılan 0.1.

Örnek (yalnızca onaylı yerel korpus ve manifest hazır olduğunda):

```bash
python tools/train_mkaos_from_scratch.py \
  --corpus ./approved-tr.jsonl \
  --manifest ./approved-manifest.json \
  --output-dir ./artifacts/mkaos-lowmem \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --warmup-steps 10 \
  --min-learning-rate-ratio 0.1
```

Örnek değerler donanım/korpuşa göre ayarlanmalıdır. Küçük bir mikro-batch ile gradyan biriktirmek büyük batch ile her durumda matematiksel olarak birebir aynı değildir; örnek sınırları, normalizasyon, sıra ve son kısmi birikim grubu gibi ayrıntılar sonuçları etkileyebilir. Bu nedenle sabit seed, aynı veri split'i ve validation kaybıyla karşılaştırmalı deney yapılmalıdır.

## Güvenlik ve doğrulama

- Eğitim betiği ağdan veri/model indirmez.
- Kaynak register, izin/lisans, PII temizliği ve train/validation/test manifest kapıları değişmeden kalır.
- Test split'i optimizer veya checkpoint seçimi için kullanılmaz; yalnızca en iyi validation checkpoint seçildikten sonra raporlanır.
- Eğitim raporu optimizer, öğrenme oranı planı, warmup, mikro-batch, accumulation, etkin batch ve toplam optimizer adımı sayısını kaydeder.
- Eğitim kaybının düşmesi, Türkçe akıl yürütme kalitesi veya frontier düzeyi zeka kanıtı değildir. Held-out görevler, insan değerlendirmesi ve hedef donanım ölçümü gerekir.
