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


## 2026-10-16 veri ve değerlendirme kapısı
- [x] Türkçe model eğitimi için kaynak/lisans/izin/PII/split kurallarını tanımlayan bağımsız değerlendirme protokolü eklendi.
- [x] Örnek başına menşe, içerik SHA-256, insan incelemesi ve train/validation/test ayrımı denetleyen metadata doğrulayıcısı eklendi: `tools/validate_mkaos_training_manifest.py`.
- [ ] Yetkili kişilerce onaylanmış gerçek veri manifesti henüz sağlanmadı; gerçek eğitim checkpoint'i üretilmedi.
- [ ] Ayrı tutulmuş, insan tarafından puanlanmış Türkçe held-out test sonuçları henüz yok.
- [ ] Fiziksel GPU/HPU cihaz testleri, ortak kalıcı dağıtık durum katmanı ve canlı mTLS peer taşıması ayrı kabul kapıları olarak açık kalıyor.

Doğrulayıcı yalnızca metadata tutarlılığı kontrol eder; lisans iznini, kaynağın doğruluğunu veya modelin niteliğini sertifikalandırmaz.


## 2026-10-16 — sıfırdan yerel model eğitim hattı
- [x] Önceden eğitilmiş model ağırlığı indirmeyen, rastgele başlatılmış MKAOS GQA/SwiGLU decoder'ı için PyTorch eğitim betiği eklendi: `tools/train_mkaos_from_scratch.py`.
- [x] UTF-8 byte tokenizer sözleşmesi ve Rust `MKAOSW1` checkpoint biçimine aktarım eklendi; Rust motoruyla aynı split-half RoPE konvansiyonu kullanılır.
- [x] Korpus içeriği SHA-256/manifest eşleştirmesi, manifest dışı örnek engeli ve boş test split'i reddi için testler eklendi.
- [ ] Eğitim için yetkili gerçek Türkçe korpus henüz sağlanmadı; eğitilmiş MKAOS checkpoint'i veya kullanılabilir Türkçe kalite sonucu henüz üretilmedi.
- [ ] Eğitilen checkpoint'in Rust decoder ile uçtan uca yükleme/üretim testi ve bağımsız Türkçe held-out değerlendirmesi henüz geçmedi.
- [ ] HTTP sohbet servisi üçüncü taraf SmolLM2 adayını kullanmaya devam ediyor; yerel model üretim varsayılanına alınmadı.
- [ ] CUDA/ROCm/Metal/Gaudi fiziksel cihaz testi, yatay Kubernetes ve paylaşılan kalıcı durum, canlı mTLS mesh/sertifika iptali ve çok düğümlü güvenlik testleri açık kabul kapıları olarak kalıyor.

Bu adım bir **eğitim altyapısı** ekler; eğitimin gerçekten çalıştırıldığı, modelin iyi Türkçe bildiği veya yüzde yüz yerli üretim sistemine ulaşıldığı iddiası değildir.

- [x] Özel checkpoint hash doğrulamasından sonra `GqaDecoder` ile greedy token üretimi yapan yerel Rust CLI eklendi: `engine/mkaos-inference/src/bin/mkaos-generate.rs`.
- [x] CI, yeni Python bütünlük testleri ve Rust crate'in tüm hedeflerini derleyip test edecek şekilde genişletildi; yeni CI sonucu henüz gözlenmedi.


## 2026-10-16 — menşe ve egemenlik güvence programı
- [x] Veri, tokenizer, model ağırlıkları, kaynak kod, transitif bağımlılıklar, derleme, dağıtım, donanım ve dağıtık güvenlik katmanları için kanıt tabanlı kabul kapıları belgelendi: docs/MKAOS_SOVEREIGNTY_ASSURANCE_PROGRAM.md.
- [x] Ağ kullanmadan yerel dosya envanteri, SHA-256, bağımlılık manifestleri, model dosyaları ve üçüncü taraf model/runtime referanslarını raporlayan denetim aracı eklendi: tools/audit_mkaos_provenance.py.
- [x] Denetim aracı için testler ve CI adımı eklendi; bu testler aracın davranışını doğrular, bağımsızlık iddiasını doğrulamaz.
- [ ] Rapor gerçek bir sürüm üzerinde çalıştırılıp her bilinmeyen için insan onaylı kanıt eklenmedi.
- [ ] Transitif lisans/SBOM, imzalı artefakt, ağsız tekrarlanabilir build ve çalışma zamanı ağ çıkışı ölçümü tamamlanmadı.
- [ ] Gerçek Türkçe korpus/checkpoint, bağımsız kalite, fiziksel hızlandırıcı, Kubernetes kalıcı durum, canlı mTLS/iptal ve çok düğümlü güvenlik kapıları hâlâ açık.

**Önemli:** Statik tarama dosya hash'lerini ve şüpheli referansları envanterler; yazar menşeini, lisans iznini, fiziksel donanımın ülke menşeini veya ağ çıkışının imkânsızlığını kanıtlamaz.
