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
- [ ] CI'da doğrulanmış başarılı çalışma
- [ ] Python/reference implementasyonuyla tolerans tabanlı diferansiyel testler

### B — Model sözleşmesi
- [x] Sürümlü model manifesti şeması
- [x] Ağırlık ve tokenizer hash alanları
- [ ] Güvenli ağırlık okuyucu ve yol geçişi koruması
- [ ] Tokenizer implementasyonu ve test vektörleri

### C — Uçtan uca küçük model
- [x] Temel embedding, RoPE ve causal mask
- [x] Tek Transformer decoder bloğu (eğitilmiş model ağırlıkları değil, test amaçlı sentetik ağırlıklar)
- [ ] Çok katmanlı decoder ve KV cache
- [ ] Final norm, LM head/logits ve greedy decoding
- [ ] Tokenizer ile uçtan uca metin üretimi
- [ ] Küçük, açık lisanslı gerçek model ağırlıklarıyla deterministik smoke test
- [ ] Kötü biçimlendirilmiş model dosyası testleri

### D — Kullanılabilirlik ve performans
- [ ] Komut satırı aracı ve yerel HTTP API
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
