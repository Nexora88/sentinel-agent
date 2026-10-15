# MKAOS bağımsız çıkarım çekirdeği

Bu crate, MKAOS'un kendi CPU çıkarım motoru için harici crate kullanmayan ve `unsafe` kodu yasaklayan Rust başlangıç katmanıdır. Şu anki bileşenler bir üretim sohbet modelinin tamamı değil; denetlenebilir matematik ve güvenli model-verisi temelleridir.

## Uygulanan bileşenler

- Boyut, taşma, NaN/sonsuz değer denetimli 2B F32 tensör; matris çarpımı/transpoz, softmax ve RMSNorm
- Token embedding lookup; çok başlıklı RoPE, causal attention, residual ve SwiGLU içeren tek decoder bloğu
- Bağımsız SHA-256 uygulaması ve bilinen test vektörleri
- Sürüm/magic imzalı `MKAOSW1\0` tensör konteyneri için sınırlandırılmış dosya okuyucu
- Yükleme sırasında beklenen SHA-256 doğrulaması; dosya boyutu, tensor sayısı, isim uzunluğu, boyut çarpımı, eleman sayısı, sonlu F32 ve dosya sonu kontrolleri
- UTF-8 byte tokenizer (yalnızca byte-level modeller ve altyapı testleri için)
- Greedy ve top-k token örnekleme yardımcıları

## Güvenli checkpoint biçimi

`checkpoint::load_checkpoint(path, expected_sha256, max_bytes, max_elements_per_tensor)` dosyayı sınırlandırılmış biçimde okur ve ayrıştırmadan önce bütün dosyanın SHA-256 değerini karşılaştırır. Biçim little-endian olarak 8 bayt magic (`MKAOSW1\0`), u32 tensor sayısı ve her tensor için u16 ad uzunluğu + UTF-8 ad + u32 satır + u32 sütun + F32LE veri içerir. Her tensor ve dosya tamamen doğrulanır; tekrarlanan adlar, eksik/trailing baytlar ve NaN/sonsuz ağırlıklar reddedilir.

Hash kontrolü **dosyanın bütünlüğünü** doğrular; modelin kaynağının veya lisansının doğru olduğunu tek başına kanıtlamaz. Beklenen hash güvenilir, bağımsız bir kaynaktan alınmalıdır. Mimariye özgü tensor adları ve şekilleri, checkpoint manifestindeki beklenen şekillerle ayrıca eşleştirilmelidir.

## Önemli sınırlar

- ByteTokenizer, SentencePiece/BPE veya yaygın önceden eğitilmiş LLM tokenizer'larıyla uyumlu değildir.
- Repo içinde lisansı ve kökeni doğrulanmış eğitilmiş bir küçük model ağırlığı henüz yoktur.
- Birden çok decoder katmanı, KV cache, final norm + LM head ile uçtan uca metin üretim döngüsü ve mimariye özgü checkpoint-to-model eşlemesi henüz tamamlanmamıştır.
- Gerçek model metni, bellek kullanımı, token/s ve gecikme karşılaştırması henüz yapılmamıştır. Sentetik ağırlıklarla test, dil kalitesi kanıtı değildir.

Bu nedenle Ollama entegrasyonu kaldırılmamalıdır. Bağımsız runtime gerçek ağırlıklarla doğrulanıp aynı değerlendirme kümesinde kalite, gecikme, RAM ve kararlılık eşiklerini geçene kadar Ollama geri dönüş seçeneği olarak kalır.

## Test

```bash
cargo test --manifest-path engine/mkaos-inference/Cargo.toml
```

Rust toolchain olmayan makinelerde test çalıştırılamaz. CI sonucu doğrulanmadan testlerin geçtiği varsayılmamalıdır.

## Geliştirme ilkeleri

1. Her kernel için matematiksel tanım, sınır koşulu ve deterministik test.
2. Harici model dosyası için lisans/menşe kaydı, dosya boyutu limiti, SHA-256 ve mimariye uygun şekil doğrulaması.
3. Tokenizer, model ağırlıkları ve model mimarisi aynı model sürümüne ait olmalı.
4. Önce F32 doğruluğu; optimizasyon ancak tekrarlanabilir benchmark sonrası.
5. Mevcut backend, bağımsız motor ölçümlerle yeterli kalite ve kararlılığı kanıtlayana kadar korunmalı.
