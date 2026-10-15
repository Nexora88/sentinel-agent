# MKAOS bağımsız çıkarım motoru yol haritası

## Mevcut durum (dürüst kapsam)

Amaç, Ollama gibi harici runtime'lara bağımlılığı ölçümle ve güvenli biçimde azaltmaktır; tek bir commit ile tam bağımsızlık iddiası yapılmaz.

Rust çekirdeğinde F32 tensör matematiği, embedding lookup, RoPE, causal attention, tek bloklu eski referans decoder, SHA-256, sınırlandırılmış MKAOSW1 checkpoint okuyucusu, byte tokenizer, greedy/top-k/top-p örnekleme ve EOS/stop-sequence destekli full-prefix üretim sürücüsü bulunur. Yeni stacked_decoder modülü çok katmanlı GQA, final RMSNorm, LM head/logits ve katman başına artımlı KV cache sunar. mkaos-hf-adapter artık standart Llama/SmolLM2 SafeTensors adlarını okuyup F32/F16/BF16 ağırlıkları F32 tensörlere dönüştüren bir yükleyici ve gerçek ağırlıklarla çalışan mkaos_generate/mkaos_logits araçları içerir. Ancak gerçek model dosyaları indirilip test edilmediği için bu yol henüz uyumlu/çalışır olarak doğrulanmış sayılmaz.

## Aşamalar

1. **Denetlenebilir CPU çekirdeği — kısmi:** matematik yardımcıları, sınır denetimleri, sentetik decoder ve testler mevcut; CI sonucu ayrıca doğrulanmalıdır.
2. **Checkpoint güvenliği — kısmi:** dosya boyutu sınırı, SHA-256, sürümlü container ve tensor şekil denetimi mevcut. Hash tek başına kaynak/lisans kanıtı değildir.
3. **Model kaynağı — kısmi:** SmolLM2-135M-Instruct için Apache-2.0 olarak listelenen model kartı ve değişmez repository revision'ı kaydedildi. Gerçek ağırlık/tokenizer SHA-256 değerleri indirilip ölçülmediği için null; henüz doğrulanmış dosya hash'i iddiası yok. İndirme aracı artık boyut sınırları içinde akışla indirip ölçülen hash'leri kilit dosyasına yazabilir; gerçek indirme henüz burada çalıştırılmadı.
4. **Safetensors dönüşümü — kısmi:** MKAOSW1 biçimine F32 taşıma dönüşümü var; mimariye özgü parametre eşleme, transpoz ve runtime uyumluluğu sağlamaz.
5. **Decoder matematiği — gerçek ağırlık yükleyici eklendi, doğrulama bekliyor:** stacked_decoder çok katman, GQA, Llama split-half RoPE, katman başına KV cache, final RMSNorm ve LM head uygular. model_loader.rs HF linear ağırlıklarını [out,in] biçiminden [in,out] biçimine transpoze eder ve F32/F16/BF16 okur. Sentetik testte artımlı logits ile full-prefix referansı karşılaştırılır; bu, gerçek model doğruluğu değildir. tools/validate_model_logits.py gerçek HF logits karşılaştırmasını çalıştırır.
6. **Model tokenizer'ı — adapter ve karşılaştırma aracı eklendi, çalıştırma bekliyor:** mkaos-hf-adapter pinned tokenizer.json dosyasını upstream Rust tokenizers ile açar. tools/validate_tokenizer.py, İngilizce/Türkçe/özel token ID'lerini Python Hugging Face tokenizer'ıyla ve chat template çıktısını transformers.apply_chat_template ile karşılaştırır. Gerçek dosyalar olmadan bu test geçilmiş sayılamaz. Tool-call/multimodal mesajlar bilinçli olarak kapsam dışı.
7. **Üretim ve benchmark — koşulabilir araçlar eklendi, gerçek koşu bekliyor:** generate_cached EOS/stop-sequence ve greedy/top-k/top-p akışını artımlı KV cache ile bağlar; sentetik test aynı greedy çıktıyı full-prefix referansıyla karşılaştırır. mkaos_generate gerçek modelde greedy üretim/ilk token/toplam süre/token-s metriklerini verir. tools/benchmark_mkaos_vs_ollama.py aynı Türkçe/İngilizce promptlarda Ollama ve MKAOS ölçümlerini JSON raporuna yazar. Bu araçlar henüz gerçek cihazda çalıştırılmadı; RAM/kalite karşılaştırması ve eşik kararı bekliyor.
8. **Kademeli geçiş:** MKAOS önce deneysel opt-in yol olur. Ollama ancak aynı donanım/test kümesinde kalite, kararlılık, bellek ve gecikme eşiklerini tekrarlı biçimde geçtikten sonra devreden çıkarılabilir.
9. **Ölçümlü optimizasyon:** önce F32 referans doğruluğu; ardından quantization/SIMD/GPU, her biri karşılaştırmalı testle.
10. **Sürekli gelişim:** kullanıcı konuşmaları varsayılan eğitim verisi yapılmaz. Açık izin, lisans, kişisel veri temizliği ve sabit holdout testleri gerekir.

## Model uyumluluğu uyarısı

SmolLM2-135M-Instruct, Llama tarzı decoder, grouped-query attention ve BPE tokenizer kullanır. Sentetik ağırlıkla çalışan decoder eklenmesi checkpoint'in doğrudan yüklenebildiği anlamına gelmez. Gerçek safetensors tensor eşlemesi, tokenizer, chat template ve referans logits doğrulaması yapılmadan model desteği ilan edilmez.

## Benchmark ölçütleri

Her rapor model ve tokenizer SHA-256, lisans/kaynak revision'ı, donanım, OS, derleme ayarları, prompt seti sürümü, seed, çıktı metni, token sayısı, görev doğruluğu, ilk-token ve toplam gecikme, token/s, tepe RSS/RAM ve hata oranını içermelidir. Aynı makine, aynı prompt seti ve mümkün olduğunca aynı hassasiyet kullanılmalıdır. Sonuçlar elde edilmeden performans üstünlüğü iddia edilmez.

## Veri ve egemenlik

- Her veri kaydı için kaynak, tarih, lisans/izin ve bütünlük hash'i tutulur.
- Arşivler ve yayınlar için toplu alma/eğitim izni varsayılmaz.
- Train/test veri sızıntısı önlenir; tartışmalı iddialar olgu gibi etiketlenmez.
- Air-gapped iddiası uygulama ayarından ibaret değildir; OS/firewall, DNS/egress denetimi ve ağ testleriyle kanıtlanmalıdır.


## Gerçek doğrulama komutları

Model dosyaları önce sabit revision'dan indirilmeli ve gerçek SHA-256 değerleri kilit dosyasına yazılmalıdır. Sonra model dizini üzerinde:

```bash
python tools/validate_tokenizer.py --model-dir models/smollm2-135m-instruct
python tools/validate_model_logits.py --model-dir models/smollm2-135m-instruct
python tools/benchmark_mkaos_vs_ollama.py --model-dir models/smollm2-135m-instruct --ollama-model <yerel-ollama-etiketi> --runs 3
```

İlk iki komutun geçmesi gerçek tokenizer/chat template ve logits uyumuna dair kapıdır. Benchmark çıktısı olmadan hız, RAM veya kalite üstünlüğü iddia edilmez. model-lock.json içindeki null SHA-256 alanları gerçek dosyalar indirilip ölçülene kadar kasıtlıdır.
