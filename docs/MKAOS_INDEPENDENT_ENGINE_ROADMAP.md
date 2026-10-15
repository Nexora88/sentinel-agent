# MKAOS bağımsız çıkarım motoru yol haritası

## Mevcut durum (dürüst kapsam)

Amaç, Ollama gibi harici runtime'lara bağımlılığı ölçümle ve güvenli biçimde azaltmaktır; tek bir commit ile tam bağımsızlık iddiası yapılmaz.

Şu an Rust çekirdeğinde F32 tensör matematiği, embedding lookup, RoPE, causal attention, tek sentetik decoder bloğu, SHA-256, sınırlandırılmış MKAOSW1 checkpoint okuyucusu, byte tokenizer, greedy/top-k/top-p örnekleme ve EOS/stop-sequence destekli full-prefix üretim sürücüsü bulunur. Full-prefix sürücü her adımda tüm prefix'i yeniden hesaplar; gerçek KV cache değildir.

## Aşamalar

1. **Denetlenebilir CPU çekirdeği — kısmi:** matematik yardımcıları, sınır denetimleri ve birim testleri mevcut; CI sonucu ayrıca doğrulanmalıdır.
2. **Checkpoint güvenliği — kısmi:** dosya boyutu sınırı, SHA-256, sürümlü container ve tensor şekil denetimi mevcut. Hash tek başına kaynak/lisans kanıtı değildir.
3. **Model kaynağı — kısmi:** SmolLM2-135M-Instruct için Apache-2.0 olarak listelenen model kartı ve değişmez repository revision'ı kaydedildi. Gerçek ağırlık/tokenizer SHA-256 değerleri indirilip ölçülmediği için null; henüz doğrulanmış dosya hash'i iddiası yok. İndirme aracı hash manifesti üretir.
4. **Safetensors dönüşümü — kısmi:** MKAOSW1 biçimine F32 taşıma dönüşümü var; mimariye özgü parametre eşleme, transpoz ve runtime uyumluluğu sağlamaz.
5. **Tam decoder — bekliyor:** çok katmanlı decoder, GQA, final RMSNorm, LM head/logits'in gerçek checkpoint'e bağlanması ve gerçek artımlı KV cache tamamlanmadı.
6. **Model tokenizer'ı — bekliyor:** mevcut ByteTokenizer yaygın BPE tokenizer ile uyumlu değil; SmolLM2 tokenizer ve chat template davranışı birebir doğrulanmalı.
7. **Benchmark — protokol hazır, ölçüm yok:** sabit Türkçe/İngilizce prompt kümesi ve ölçüm protokolü eklendi. Gerçek model yüklenmeden doğruluk, ilk-token gecikmesi, toplam gecikme, token/s ve tepe RSS ölçülemez.
8. **Kademeli geçiş:** MKAOS önce deneysel opt-in yol olur. Ollama ancak aynı donanım/test kümesinde kalite, kararlılık, bellek ve gecikme eşiklerini tekrarlı biçimde geçtikten sonra devreden çıkarılabilir.
9. **Ölçümlü optimizasyon:** önce F32 referans doğruluğu; ardından quantization/SIMD/GPU, her biri karşılaştırmalı testle.
10. **Sürekli gelişim:** kullanıcı konuşmaları varsayılan eğitim verisi yapılmaz. Açık izin, lisans, kişisel veri temizliği ve sabit holdout testleri gerekir.

## Model uyumluluğu uyarısı

SmolLM2-135M-Instruct, Llama tarzı decoder, grouped-query attention ve BPE tokenizer kullanır. Mevcut Rust çekirdeği bunları henüz desteklemediğinden checkpoint'in MKAOSW1'e dönüştürülmesi modeli çalışır kılmaz. Eğitim ağırlığı veya tokenizer uyumluluğu kanıtlanmadan metin kalitesi iddiası yapılmaz.

## Benchmark ölçütleri

Her rapor model ve tokenizer SHA-256, lisans/kaynak revision'ı, donanım, OS, derleme ayarları, prompt seti sürümü, seed, çıktı metni, token sayısı, görev doğruluğu, ilk-token ve toplam gecikme, token/s, tepe RSS/RAM ve hata oranını içermelidir. Aynı makine, aynı prompt seti ve mümkün olduğunca aynı hassasiyet kullanılmalıdır. Sonuçlar elde edilmeden performans üstünlüğü iddia edilmez.

## Veri ve egemenlik

- Her veri kaydı için kaynak, tarih, lisans/izin ve bütünlük hash'i tutulur.
- Arşivler ve yayınlar için toplu alma/eğitim izni varsayılmaz.
- Train/test veri sızıntısı önlenir; tartışmalı iddialar olgu gibi etiketlenmez.
- Air-gapped iddiası uygulama ayarından ibaret değildir; OS/firewall, DNS/egress denetimi ve ağ testleriyle kanıtlanmalıdır.
