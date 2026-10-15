# MKAOS bağımsız çıkarım çekirdeği

Bu crate, MKAOS'un kendi CPU çıkarım motoru için başlangıçtır. Harici Rust crate bağımlılığı kullanmaz ve `unsafe` kodu yasaktır.

## Şu anda uygulananlar

- Güvenli şekil doğrulamalı 2B F32 tensör
- Matris çarpımı ve transpoz
- Kararlı satır bazlı softmax
- RMS normalizasyonu
- Referans scaled dot-product attention (Q/K/V)

## Henüz uygulanmayanlar

Bu sürüm **tek başına sohbet modeli çalıştırmaz**. Tokenizer, model ağırlığı okuyucu, embedding, RoPE, causal mask, Transformer decoder, KV cache, kuantizasyon, sampling, sohbet API'si ve GPU kernel'leri henüz yoktur. Bu nedenle üretimdeki Ollama entegrasyonunu bu aşamada silmek, çalışan yerel sohbeti kırar ve bağımsızlık sağlamaz.

## Geliştirme ilkeleri

1. Her operasyonda matematiksel tanım ve küçük deterministik test bulunmalı.
2. Bir sonraki katman, bu katmanın testleri geçmeden eklenmemeli.
3. Harici model ağırlıkları için model kartı, lisans, tokenizer ve SHA-256 doğrulaması zorunlu olmalı.
4. Model çalıştırıcısı hazır olana kadar mevcut backend geçiş köprüsü olarak kalmalı; uzak/bulut uç noktaları varsayılan olmamalı.
5. Bağımsız runtime mevcut iş akışlarında kalite, gecikme, RAM/VRAM ve kararlılık eşiklerini geçince varsayılan hâle getirilmeli.

## Test

```bash
cargo test --manifest-path engine/mkaos-inference/Cargo.toml
```

Bu komut internet veya üçüncü taraf crate indirmesi gerektirmemelidir.
