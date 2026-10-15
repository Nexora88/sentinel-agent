# MKAOS bağımsız çıkarım çekirdeği

Bu crate, MKAOS'un kendi CPU çıkarım motoru için başlangıçtır. Harici Rust crate bağımlılığı kullanmaz ve `unsafe` kodu yasaktır.

## Şu anda uygulananlar

- Şekil ve NaN/sonsuz değer doğrulamalı 2B F32 tensör
- Matris çarpımı, transpoz, ölçekleme ve satır işlemleri
- Kararlı satır bazlı softmax ve RMSNorm (öğrenilebilir ölçek vektörü uygulaması dahil)
- Token ID → embedding tablosu lookup
- Çok başlıklı RoPE konumsal kodlama
- Gelecek tokenları dışlayan nedensel (causal) attention maskesi
- Q/K/V projeksiyonları, attention çıktı projeksiyonu ve residual bağlantıları
- SwiGLU ileri beslemeli ağ
- Tek Transformer decoder bloğu için uçtan uca referans forward pass
- Deterministik birim testleri; özellikle gelecekteki değerlerin önceki token çıktısını etkilemediğini sınayan test

## Bilinçli sınırlar

Bu sürüm hâlâ **tam bir sohbet modeli/runtime değildir**. Tokenizer, güvenli checkpoint/model ağırlığı okuyucu, gerçek bir eğitilmiş model dosyası, birden çok decoder bloğunu yöneten model konfigürasyonu, son-normalizasyon + LM head/logit üretimi, token sampling, KV cache, batching, kuantizasyon, SIMD/GPU kernel'leri ve sohbet API'si henüz yoktur. Decoder ağırlıkları şu an çağıran kod tarafından bellekte sağlanır; repo içinde doğrulanmış bir üretim modeli bulunması anlamına gelmez.

Bu nedenle çalışan Ollama entegrasyonunu henüz silmek, kullanılabilir sohbeti kırabilir. Önce lisansı ve kaynağı doğrulanmış küçük bir model için dosya biçimi, tokenizer ve uçtan uca metin üretimi tamamlanmalıdır.

## Test

```bash
cargo test --manifest-path engine/mkaos-inference/Cargo.toml
```

Çekirdek kaynak kodu üçüncü taraf Rust crate kullanmaz. Cargo test, manifestte bağımlılık olmadığı sürece harici crate indirmemelidir. Rust toolchain bulunmayan makinelerde test çalıştırılamaz; CI sonucu görülmeden testlerin geçtiği varsayılmamalıdır.

## Geliştirme ilkeleri

1. Her operasyonda matematiksel tanım ve deterministik test bulunmalı.
2. Sayısal kararlılık, boyut doğrulaması ve bozuk model girdileri test edilmeli.
3. Harici model ağırlıkları için model kartı, lisans, tokenizer ve SHA-256 doğrulaması zorunlu olmalı.
4. Model çalıştırıcısı hazır olana kadar mevcut backend geçiş köprüsü olarak kalmalı; uzak/bulut uç noktaları varsayılan olmamalı.
5. Bağımsız runtime mevcut iş akışlarında kalite, gecikme, RAM/VRAM ve kararlılık eşiklerini geçince varsayılan hâle getirilmeli.
