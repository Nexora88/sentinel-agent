# MKAOS bağımsız çıkarım motoru yol haritası

## Hedef ve doğrulanmış kapsam

Amaç, model çalışma zamanı üzerindeki mimari kontrolü artırıp Ollama gibi harici çalışma zamanlarına zorunlu bağımlılığı kontrollü biçimde azaltmaktır. Tek bir değişiklikle tam bağımsızlık iddiası yapılmaz.

Şu an çekirdekte F32 tensörler, embedding lookup, RoPE, causal attention, tek decoder bloğu, SHA-256, sınırlandırılmış özel checkpoint okuyucusu, byte tokenizer ve token sampling yardımcıları bulunur. Bunlar temel altyapıdır; henüz eğitilmiş bir dil modelini uçtan uca çalıştıran runtime değildir.

## Aşamalar

1. **Denetlenebilir CPU çekirdeği:** boyut/taşma/NaN denetimleri, deterministik testler ve referans karşılaştırmaları.
2. **Checkpoint güvenliği:** dosya boyutu sınırı, SHA-256, sürümlü container, tensor isim/şekil doğrulaması ve lisans/menşe manifesti. Hash tek başına kaynak veya lisans doğrulaması değildir.
3. **Tokenizer + lisanslı küçük model:** model kartı, lisans, kaynak URL, tokenizer dosyaları ve ağırlık hash'leri birlikte sabitlenir. ByteTokenizer yalnızca altyapı/test tokenizer'ıdır; BPE/SentencePiece yerine geçtiği iddia edilmez.
4. **Tam decoder:** birden fazla katman, final norm, LM head, logits, EOS/stop yönetimi, greedy/top-k/top-p örnekleme ve gerçek K/V cache. Artımlı decode ile tüm prefix'i yeniden hesaplayan referans çıktıları tolerans içinde karşılaştırılır.
5. **Güvenli model bağlama:** manifestteki her tensor adı ve şekli beklenen mimariyle karşılaştırılır; eksik, fazla veya uyuşmayan tensorlar yüklenmez.
6. **Benchmark:** aynı prompt/test kümesinde metin çıktısı, görev doğruluğu, ilk token gecikmesi, token/s, toplam gecikme, tepe RSS/RAM, model boyutu ve hata oranı kaydedilir. Donanım, işletim sistemi, build profili, seed ve model hash'i rapora eklenir.
7. **Kademeli geçiş:** bağımsız motor önce opt-in/deneysel seçenek, sonra kontrollü küçük kullanıcı grubu; kalite ve kararlılık eşiklerini tekrar tekrar geçtiğinde varsayılan. Ollama ancak bağımsız yolun işlevsel eşdeğerliği kanıtlanırsa kaldırılır.
8. **Ölçümlü optimizasyon:** F32 referansından sonra quantization/SIMD/GPU. Her optimizasyon önceki sonuçla doğruluk ve bellek karşılaştırmasına tabi tutulur.
9. **Sürekli gelişim:** kullanıcı konuşmaları varsayılan eğitim verisi olmaz. Açık izin, lisans, kişisel veri temizliği, insan değerlendirmesi ve sabit holdout seti gerekir; aday model otomatik olarak kararlı sürümün üzerine yazılmaz.

## Türkçe veri ve egemenlik

- Her veri kaydı için kaynak, tarih, lisans/izin ve bütünlük hash'i kaydedilir; kurum adı tek başına yeniden kullanım hakkı değildir.
- Arşivler ve akademik yayınlar için toplu alma/eğitim izni varsayılmaz.
- Tarihî iddialar mümkün olduğunda birincil kaynak ve çapraz kontrol ile değerlendirilir; tartışmalı iddialar olgu gibi etiketlenmez.
- Train/test veri sızıntısı engellenir; veri seti manifesti ve reddedilen kayıt raporu sürümlenir.
- Air-gapped iddiası sadece uygulama ayarıyla değil, işletim sistemi/firewall, DNS/egress kontrolleri ve ağ testleriyle doğrulanır.

## Başarı ölçütleri

Her benchmark raporu model hash'i, lisans, donanım, OS, derleme ayarları, prompt/test seti sürümü, seed, token sayısı, doğruluk, ilk-token ve toplam gecikme, token/s, tepe RAM ve hata oranını içermelidir. Ollama karşılaştırması aynı makine ve aynı test setiyle yapılmalıdır. Sonuçlar elde edilmeden performans veya kalite üstünlüğü iddia edilmez.
