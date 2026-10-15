# MKAOS dış çalışma zamanı bağımlılığını azaltma planı

## Hedef

Uzun vadeli hedef, MKAOS'un kendi model dosya biçimi, tokenizer'ı, CPU çıkarım motoru, testleri ve dağıtım paketine sahip olmasıdır. Bağımsızlık, başka bir projeyi yalnızca yeniden adlandırmak değildir: kaynak kodu denetlenebilir, lisansı uygun, sürümlenebilir ve sürdürülebilir bir runtime gerektirir.

## Geçiş kapıları

### A — Çekirdek hesaplama
- [x] Harici crate kullanmayan Rust crate
- [x] Matris çarpımı, transpoz, softmax, RMSNorm
- [x] Referans scaled dot-product attention
- [x] Token embedding lookup, RoPE, causal mask, çok başlıklı attention, residual ve SwiGLU
- [x] Tek decoder bloğu için sentetik ağırlıklarla uçtan uca forward-pass testi
- [x] CI'da doğrulanmış başarılı çalışma
- [ ] Python/reference implementasyonuyla tolerans tabanlı diferansiyel testler

### B — Model sözleşmesi
- [x] Sürümlü model manifesti şeması
- [x] Ağırlık ve tokenizer hash alanları
- [x] Boyut sınırları ve SHA-256 doğrulaması olan güvenli özel checkpoint okuyucusu
- [x] Checkpoint tensor ad/şekillerini manifest ile karşılaştıran doğrulayıcı
- [ ] Model dosyası dışa açılan bir API'ye bağlanmadan önce path traversal/symlink tehdit modelinin test edilmesi
- [x] Altyapı için UTF-8 byte tokenizer ve test vektörleri (BPE/SentencePiece uyumlu değildir)
- [x] Greedy ve top-k örnekleme yardımcıları

### C — Uçtan uca küçük model
- [x] Temel embedding, RoPE ve causal mask
- [x] Tek Transformer decoder bloğu (eğitilmiş model ağırlıkları değil, test amaçlı sentetik ağırlıklar)
- [x] Çok katmanlı decoder ve KV cache
- [x] Final norm, LM head/logits ve greedy decoding
- [x] Tokenizer ile uçtan uca metin üretimi
- [x] Küçük, açık lisanslı gerçek model ağırlıklarıyla deterministik smoke test (pinned SmolLM2-135M, logits/tokenizer parity passed)
- [x] Hash uyuşmazlığı, hatalı hash formatı ve tensor manifest uyuşmazlığı testleri
- [ ] Geçerli checkpoint round-trip ve fuzz/property testleri

### D — Kullanılabilirlik ve performans
- [x] Komut satırı aracı (CLI); [ ] yerel HTTP API
- [ ] RAM, gecikme p50/p95, token/s ve kalite raporu
- [ ] Düşük bellekli CPU testleri
- [ ] Gerçek donanımda doğrulanmış SIMD/GPU desteği

### E — Mevcut MKAOS uygulamasına geçiş
- [ ] Backend arayüzü ve yapılandırılabilir motor seçimi
- [ ] Mevcut test senaryolarında kalite/işlev karşılaştırması
- [ ] MKAOS motoruyla varsayılan yerel sohbet akışı
- [ ] Eski backend yalnızca geçiş/karşılaştırma seçeneği olarak
- [ ] Başarılı geri alma provası ve dokümantasyon

**Kabul ölçütü:** Ollama ancak MKAOS motoru gerçek model üzerinde tekrarlanabilir uçtan uca yanıt üretip gerekli regresyon, güvenlik, bellek ve kararlılık eşiklerini karşıladıktan sonra varsayılan dağıtımdan çıkarılabilir. O noktaya kadar bağımlılığı gizlice silmek yerine açıkça geçici olarak işaretlemek daha güvenlidir.

## Egemenlik kontrol listesi

- Çevrimdışı derleme ve test için gerekli tüm bağımlılıklar önceden sabitlenmeli.
- Model ağırlıkları, tokenizer, veri seti ve kodun ayrı ayrı lisans/menşe kayıtları olmalı.
- Ağ erişimi yalnızca uygulama ayarıyla değil, OS/firewall ve dağıtım politikalarıyla sınırlandırılmalı.
- Telemetri kapalı varsayılan olmalı; gizli veri veya istemler test/benchmark raporlarına yazılmamalı.
- Tarihsel/kültürel cevaplar kaynak, tarih, bağlam ve belirsizlik taşımalı; model millî kimlik adına uydurma kaynak üretmemeli.
- Model eğitimi için yalnızca izinli, denetlenmiş ve kişisel veriden arındırılmış veri kullanılmalı.


## 2026-10-15 doğrulama notu
- Gerçek, sabitlenmiş SmolLM2-135M-Instruct ağırlıkları ile Rust motoru için iki prompt'ta HF referans logits doğrulaması geçti: maksimum mutlak hata yaklaşık 0.0000816 altında; kosinüs benzerliği yaklaşık 1.0; tepe token eşleşti.
- Tokenizer ID örnekleri ve sohbet şablonu Hugging Face referansıyla eşleşti.
- Model/tokenizer dosyalarının SHA-256 değerleri CI indirmesinde ölçüldü ve model kilit dosyasına yazıldı.
- Bu kanıtlar **test edilen forward-pass uyumluluğunu** gösterir; Türkçe genel kalite, hız, bellek, uzun süreli kararlılık, eğitimle kendi ağırlıklarını üretme veya üretim güvenliği kanıtı değildir.
- Ollama ile aynı cihaz karşılaştırması ve ağsız konteyner testi ayrı kabul kapılarıdır; tamamlanana kadar Ollama'yı kaldırmayın.
