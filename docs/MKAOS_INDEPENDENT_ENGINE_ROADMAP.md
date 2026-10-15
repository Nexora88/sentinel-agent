# MKAOS bağımsız çıkarım motoru yol haritası

## Mevcut durum (dürüst kapsam)

Amaç, Ollama gibi harici runtime'lara bağımlılığı ölçümle ve güvenli biçimde azaltmaktır; tek bir commit ile tam bağımsızlık iddiası yapılmaz.

Rust çekirdeğinde F32 tensör matematiği, embedding lookup, RoPE, causal attention, tek bloklu eski referans decoder, SHA-256, sınırlandırılmış MKAOSW1 checkpoint okuyucusu, byte tokenizer, greedy/top-k/top-p örnekleme ve EOS/stop-sequence destekli full-prefix üretim sürücüsü bulunur. Yeni `stacked_decoder` modülü ayrıca çok katmanlı GQA, final RMSNorm, LM head/logits ve her katmana ayrı artımlı KV cache için sentetik ağırlıklarla çalışan referans yol sunar. Bu modül henüz SmolLM2'nin gerçek dosyalarından ağırlık yüklemez.

## Aşamalar

1. **Denetlenebilir CPU çekirdeği — kısmi:** matematik yardımcıları, sınır denetimleri, sentetik decoder ve testler mevcut; CI sonucu ayrıca doğrulanmalıdır.
2. **Checkpoint güvenliği — kısmi:** dosya boyutu sınırı, SHA-256, sürümlü container ve tensor şekil denetimi mevcut. Hash tek başına kaynak/lisans kanıtı değildir.
3. **Model kaynağı — kısmi:** SmolLM2-135M-Instruct için Apache-2.0 olarak listelenen model kartı ve değişmez repository revision'ı kaydedildi. Gerçek ağırlık/tokenizer SHA-256 değerleri indirilip ölçülmediği için null; henüz doğrulanmış dosya hash'i iddiası yok. İndirme aracı artık boyut sınırları içinde akışla indirip ölçülen hash'leri kilit dosyasına yazabilir; gerçek indirme henüz burada çalıştırılmadı.
4. **Safetensors dönüşümü — kısmi:** MKAOSW1 biçimine F32 taşıma dönüşümü var; mimariye özgü parametre eşleme, transpoz ve runtime uyumluluğu sağlamaz.
5. **Decoder matematiği — yeni referans eklendi, model uyumluluğu bekliyor:** `stacked_decoder` birden fazla katmanı, GQA head eşlemesini, RoPE, katman başına KV cache'i, final RMSNorm ve LM head logits'ini uygular. Sentetik küçük ağırlıklarla tasarlandı. Gerçek checkpoint isim/şekil eşlemesi, BF16 dönüşüm doğrulaması ve Hugging Face referans logits karşılaştırması henüz yok.
6. **Model tokenizer'ı — kısmi:** ayrı `mkaos-hf-adapter` crate, pinned `tokenizer.json` dosyasını Hugging Face `tokenizers` kütüphanesiyle açan BPE/normalizer/pre-tokenizer/added-token adapter'ı ve SmolLM2 metin chat çerçevesi sunar. Chat framing birim testleri eklendi; gerçek pinned tokenizer dosyasıyla encode/decode karşılaştırması CI'da henüz yapılamadı çünkü model dosyaları depoda yok. Tool-call/multimodal mesajlar bilinçli olarak kapsam dışı.
7. **Gerçek üretim ve benchmark — bekliyor:** mevcut full-prefix üretim sürücüsü her adımda tüm prefix'i yeniden hesaplar; yeni KV-cache decoder ise tek token adımı sunar fakat henüz generation trait/stop koşullarıyla gerçek model adapter'ına bağlanmadı. Sabit Türkçe/İngilizce prompt seti ve ölçüm protokolü hazır; gerçek model yüklenmeden doğruluk, ilk-token gecikmesi, toplam gecikme, token/s ve tepe RSS ölçülemez.
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
