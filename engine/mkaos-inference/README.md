# MKAOS bağımsız çıkarım çekirdeği

Bu crate, MKAOS'un denetlenebilir CPU çıkarım motoru için harici Rust crate gerektirmeyen ve unsafe kodu yasaklayan başlangıç katmanıdır. Henüz eğitilmiş bir modeli uçtan uca çalıştıran üretim runtime'ı değildir.

## Mevcut altyapı

- F32 tensör matematiği, matris çarpımı, softmax ve RMSNorm.
- Tek sentetik Transformer decoder bloğu: embedding, RoPE, causal multi-head attention, residual ve SwiGLU.
- SHA-256 ve sınırlandırılmış MKAOSW1 checkpoint okuyucusu; beklenen hash, dosya sınırı, tensor şekli ve sonlu ağırlık denetimleri.
- UTF-8 byte tokenizer (yaygın BPE/SentencePiece modelleriyle uyumlu değildir).
- Greedy, top-k ve top-p örnekleme.
- EOS ve token dizisiyle durdurma destekli referans üretim döngüsü.

## Gerçek model adayı

models/smollm2-135m-instruct/model-lock.json dosyası, Apache-2.0 olarak listelenen SmolLM2-135M-Instruct modelinin değişmez kaynak revision'ını ve tokenizer/ağırlık URL'lerini kaydeder. Revision sabitlenmiştir; dosyaların SHA-256 değerleri bu ortamda gerçek dosyalar indirilip ölçülmediğinden henüz null'dır. Hash uydurulmamıştır. Ağ erişimi olan ortamda tools/fetch_model.py çalıştırılarak dosya hash'leri üretilebilir.

Bu aday LlamaForCausalLM, grouped-query attention ve BPE tokenizer kullanır. Mevcut Rust decoder bu mimariyle uyumlu değildir. Bu nedenle model henüz Rust motorunda çalıştırılabilir kabul edilmez. tools/convert_safetensors_to_mkaosw1.py yalnızca format dönüşümü yapar; mimari parametre eşlemesi sağlamaz.

## Üretim döngüsü sınırları

Generation sürücüsü EOS ve durdurma dizilerini destekler; ancak her token için tüm prefix'i yeniden hesaplar. Bu gerçek KV cache değildir. Çok katmanlı decoder, GQA, model uyumlu tokenizer, final norm/LM head'in gerçek checkpoint ile bağlanması ve artımlı KV-cache decode hâlâ yapılmalıdır.

## Test

cargo test --manifest-path engine/mkaos-inference/Cargo.toml

Rust testleri CI çalışması doğrulanmadan başarılı sayılmaz. Sentetik testler model kalitesi kanıtı değildir. Ollama, gerçek model ve aynı prompt kümesindeki kalite/kararlılık/RAM/gecikme ölçümleri yeterli olana kadar korunur.
