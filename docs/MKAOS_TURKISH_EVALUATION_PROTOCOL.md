# MKAOS Türkçe eğitim ve bağımsız değerlendirme kapısı

Bu belge bir eğitim sonucu duyurusu değildir. Amaç, MKAOS'un kendi ağırlıklarını üretmeden önce izinli veri ve bağımsız ölçüm altyapısını denetlenebilir hâle getirmektir.

## Eğitim veri kapısı

1. Her örnek kaynak kimliği/URL'si, lisans, izin dayanağı, SHA-256, dil, konu, insan incelemesi, PII durumu ve split bilgisi taşır.
2. Lisans/kullanım izni belirsiz, insan incelemesi bekleyen veya PII temizliği doğrulanmamış örnekler eğitimden çıkarılır.
3. İçerik hash'i tekrarı deduplikasyon hatasıdır. Train, validation ve test kümeleri ayrı tutulur; test kümesi prompt/hiperparametre ayarlamasında kullanılmaz.
4. Manifest doğrulayıcı metadata tutarlılığını denetler. Lisansın hukuken uygun olduğunu, kaynağın gerçekliğini ya da örneğin doğruluğunu tek başına kanıtlamaz. Yetkili insan incelemesi zorunludur.

Komutlar:

    python tools/validate_mkaos_training_manifest.py path/to/approved-manifest.json
    python -m unittest discover -s tests -p test_mkaos_training_manifest.py -v

## Bağımsız Türkçe değerlendirme protokolü

Mevcut benchmarks/mkaos-quality-tr-001.json küçük bir regresyon/smoke kümesidir; bağımsız uzman değerlendirmesi veya gerçek Türkçe yeterlilik kanıtı değildir. Kendi modelimizin iddiası için:

- Model adı, checkpoint SHA-256, tokenizer hash'i, eğitim verisi revizyonu, quantization, runtime commit'i ve cihaz bilgisi rapora yazılmalı.
- Sabit ve sürümlenmiş test kümesi eğitim ve geliştirme verisinden ayrı bir ekip/kişi tarafından tutulmalı.
- Kapsam Türkçe anlama, dilbilgisi, talimat izleme, çok adımlı mantık, matematik, kod, kaynak doğruluğu, güvenlik ve tekrar ölçümlerini içermeli.
- Otomatik metrikler (exact/substring, tekrar oranı, gecikme) insan puanlamasının yerine geçmemeli. En az iki değerlendirici, önceden tanımlı rubrik ve uyuşmazlık çözümü kullanılmalı.
- Sonuçlar hem mutlak puan hem görev bazlı hata dökümü olarak raporlanmalı. Sadece ortalama puan veya seçilmiş örnekler yayımlanmamalı.
- Test setine erişen kişi/işlem günlüğü tutulmalı; test örnekleri eğitim verisine karışırsa o sürüm artık bağımsız held-out kabul edilmemeli.

## Model geliştirme aşamaları

1. Veri onayı: gerçek kaynaklar, izinler, PII temizliği, deduplikasyon ve manifest.
2. Temel ölçüm: mevcut SmolLM2 taban çizgisini ve mevcut MKAOS motorunu aynı sabit testlerde çalıştır.
3. İlk MKAOS checkpoint'i: yalnızca veri/lisans kapısı geçtikten sonra küçük, tekrar üretilebilir eğitim/ince ayar denemesi; seed, optimizer, tokenizer, kod commit'i ve hiperparametreleri kaydet.
4. Kabul testi: test kümesine dokunmadan en az iki bağımsız değerlendirici; Türkçe kalite, tekrar, güvenlik, bellek ve hız eşikleri.
5. Yayın: model kartı, dataset card, ağırlık ve tokenizer hash'leri, lisanslar, bilinen sınırlamalar ve insan onaylı yayın/geri alma.

Gerçek veri ve yeterli eğitim hesaplama kaynağı sağlanmadan kendi eğitilmiş LLM sonucu üretilemez. Sentetik CI ağırlıkları sadece motorun testidir; gerçek Türkçe bilgi/akıl yürütme yeteneği oluşturmaz.
