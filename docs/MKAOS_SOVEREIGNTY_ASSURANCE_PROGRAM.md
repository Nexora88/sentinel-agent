# MKAOS bağımsızlık ve yerli menşe güvence programı

**Durum: hedef ve denetim planı; yerli/egemenlik sertifikası değildir.** Bu belge, MKAOS'un tüm kritik katmanlarında ölçülebilir kabul kapıları tanımlar. Bir bileşenin Rust/Python ile yazılmış olması, tek başına yerli menşe, hukuki uygunluk veya güvenlik kanıtı değildir.

## Bağımsızlık tanımı

Bir sürüm ancak aşağıdaki katmanların her biri kanıtla değerlendirilince “tam bağımsız” olarak nitelenebilir:

1. **Kaynak ve fikrî haklar:** kodun yazarı/menşei, lisans, patent ve katkı kayıtları.
2. **Eğitim verisi:** kaynak, kullanım izni, kişisel veri, telif/lisans incelemesi, deduplikasyon, veri kartı ve sürüm hash'i.
3. **Tokenizer:** algoritma ve eğitim korpusu, kaynak kod, test vektörleri, lisans ve sürüm hash'i. UTF-8 byte tokenizer yalnızca geçiş altyapısıdır; olgun Türkçe tokenizer değildir.
4. **Model mimarisi ve ağırlıklar:** mimari belgesi, rastgele başlatma/optimizer/seed, eğitim günlüğü, checkpoint hash'i, veri revizyonu, lisans ve tekrar üretilebilirlik. Üçüncü taraf ağırlıkların yeniden adlandırılması kabul edilmez.
5. **Çıkarım ve servis:** yerel kod, API, tokenizer uyumu, kaynak kod/ikili eşleşmesi, ağ çıkışı varsayılanı, hata ve geri alma davranışı.
6. **Yazılım tedarik zinciri:** doğrudan ve transitif paketler, sürümler, hash/checksum, lisanslar, SBOM, imzalı artefakt, derleme araç zinciri ve güvenlik duyuruları.
7. **Derleme ve dağıtım:** ağsız temiz ortamda tekrarlanabilir derleme, imaj/provenance, imzalama, anahtar yönetimi, güncelleme ve geri alma.
8. **Donanım ve ürün:** hedef CPU/GPU/HPU, sürücü/firmware, bellek/latans/throughput, uzun süreli kararlılık ve hata enjeksiyonu.
9. **Dağıtık çalışma:** Kubernetes ölçekleme, kalıcı oturum ve bellek, tutarlılık, tenant izolasyonu, mTLS, kimlik doğrulama, sertifika/anahtar iptali, düğüm kaybı ve saldırı testleri.
10. **İnsan denetimi:** bağımsız Türkçe benchmark, en az iki değerlendirici, güvenlik testi, raporların imzalı ve sürümlü yayımlanması.

“Türkiye'de geliştirildi”, “açık kaynak”, “internetsiz çalışabilir” ve “tamamen yerli” farklı iddialardır; birbirlerinin yerine kullanılmamalıdır. Yurt dışı menşeli bir derleyici, GPU sürücüsü, donanım veya kütüphane varsa bunun etkisi ayrı kaydedilmelidir. Yazılımın kendi kodunu üretmesi bu menşei ortadan kaldırmaz.

## Geçiş kapıları — sıralama zorunludur

### G0 — Envanter ve tehdit modeli
- [ ] Tüm çalışma zamanı/derleme bağımlılıklarını (transitifler dahil) sürüm, kaynak, lisans, hash ve bakım durumu ile kaydet.
- [ ] Model, tokenizer, korpus, örnek veri, test seti ve dağıtım imajlarını ayrı envanterle.
- [ ] Ağ çıkışlarını (DNS, HTTP(S), telemetry, crash reporting, package/model download) sınıflandır ve izin listesi oluştur.
- [ ] Tehdit modeli: kötü niyetli paket, bozuk checkpoint, prompt injection, veri zehirleme, model inversion, tenant kaçışı, çalınmış imzalama anahtarı, tedarik zinciri ihlali.
- [ ] tools/audit_mkaos_provenance.py raporunu üret; her UNVERIFIED için sorumlu, kanıt ve hedef tarih ata.

### G1 — Veri hukuku ve veri kalitesi
- [ ] Kaynak başına lisans/izin incelemesi ve saklama şartları yazılı onaylansın.
- [ ] Kişisel veriler için hukuki dayanak, minimizasyon, silme/itiraz süreci ve veri koruma incelemesi belgelensin.
- [ ] Türkçe karakter, ağız/lehçe, tarihî dil, kod ve alan bilgisi temsili ölçülsün.
- [ ] Deduplication, zehirleme taraması, PII taraması, train/validation/test izolasyonu ve veri kartı doğrulansın.
- [ ] Gerçek onaylı manifest ve içerik hash'leri oluşturulsun; test verisi eğitimden erişim bakımından ayrıştırılsın.

### G2 — Kendi tokenizer'ımız ve modelimiz
- [ ] Türkçe ağırlıklı tokenizer yaklaşımı seçilsin; byte tokenizer başlangıç çizgisiyle karşılaştırma raporu çıkarılsın.
- [ ] Tokenizer yalnızca lisansı/onayı belgeli veriyle eğitilsin; normalizasyon ve Unicode testleri eklensin.
- [ ] Mimari, parametre sayısı, bağlam penceresi, eğitim FLOPs/enerji, optimizer, seed ve veri sırası kayıt altına alınsın.
- [ ] Rastgele başlatmadan tam eğitim koşusu ve checkpoint hash'i üret; kısmi/deneysel checkpoint'i üretim modeli diye sunma.
- [ ] Aynı kod, veri revizyonu ve seed ile mümkün olan ölçüde tekrarlanabilir eğitim testi yapılsın.

### G3 — Model doğruluğu ve Türkçe kalite
- [ ] Eğitimden bağımsız, gizli tutulan sürümlü benchmark hazırlanıp erişimi kayıt altına alınsın.
- [ ] En az iki bağımsız değerlendirici kör puanlama yapsın; uyuşmazlık çözümü ve rubrik yayımlansın.
- [ ] Türkçe anlama/yazma, talimat izleme, muhakeme, matematik, kod, bilgi doğruluğu, kaynak uydurma, güvenlik ve red davranışı ölçülsün.
- [ ] SmolLM2 yalnızca açıkça etiketlenmiş tarihsel taban çizgisi olarak karşılaştırılsın; bağımsız MKAOS iddiasında kullanılmasın.
- [ ] Regresyon eşiği, minimum kalite, güvenlik, tekrar ve gecikme eşikleri önceden belirlensin.

### G4 — Yerel servis geçişi
- [ ] Rust checkpoint yükleme/üretim yolu gerçek kendi checkpoint'imizle uçtan uca geçsin.
- [ ] HTTP backend arayüzü MKAOS yerel motorunu seçebilsin; model sağlayıcıları açık allowlist ile sınırlansın.
- [ ] İlk aşamada opt-in canary; eski adayla karşılaştırma, gözlemlenebilirlik ve geri alma.
- [ ] Bağımsız model tüm kabul eşiklerini geçmeden üçüncü taraf ağırlıkları varsayılan yoldan kaldırma/yerine koyma işlemi yapılmasın.
- [ ] Üretim artefaktında model/tokenizer/data/runtime hash'leri doğrulansın.

### G5 — Tedarik zinciri ve ağsız çalışma
- [ ] Python/Rust/OS bağımlılıkları kilitlensin; lisans ve güvenlik taraması yapılıp istisnalar belgelenmiş olsun.
- [ ] SPDX veya CycloneDX SBOM oluşturulsun; artefaktlar hash'lenip imzalansın.
- [ ] Bağımlılıklar önceden edinildikten sonra temiz ortamda ağ kapalı build/test çalışsın.
- [ ] Çalışma anı ağ çıkışı firewall seviyesinde engellenip paket yakalama/denetimle doğrulansın.
- [ ] Güncelleme imza doğrulama, rollback, anahtar rotasyonu ve olay müdahalesi tatbikatı yapılsın.

### G6 — Donanım ve performans
- [ ] CPU referans cihazında doğruluk, bellek, gecikme p50/p95, token/s, 24–72 saat kararlılık.
- [ ] CUDA, ROCm, Metal ve Gaudi yalnızca ilgili fiziksel/erişilebilir donanımda doğrulansın; emülasyon gerçek cihaz testi sayılmaz.
- [ ] Her backend aynı checkpoint için tolerans tabanlı sayısal uyum testinden geçsin.
- [ ] Enerji tüketimi, termal throttling, bellek sınırları ve düşük kaynak davranışı raporlansın.

### G7 — Dağıtık ve kurumsal güvenlik
- [ ] Kubernetes ölçekleme, health/readiness, graceful shutdown ve kapasite baskısı testleri.
- [ ] Paylaşılan kalıcı oturum/bellek deposu; tutarlılık, şifreleme, tenant izolasyonu, yedek/geri yükleme ve veri silme testleri.
- [ ] Gerçek mTLS peer taşıması, kimlik/sertifika yaşam döngüsü, iptal listesi/OCSP veya belirlenmiş eşdeğer iptal mekanizması.
- [ ] Düğüm kaybı, replay, sahte peer, süre aşımı, ağ bölünmesi ve anahtar rotasyonu senaryoları.
- [ ] Bağımsız tehdit modellemesi ve çok düğümlü güvenlik incelemesi.

## Otomatik menşe raporu

python tools/audit_mkaos_provenance.py --root . --output artifacts/mkaos-provenance-audit.json komutu yerel dosyaların hash'lerini ve bilinen bağımlılık/model işaretlerini envantere alır. Bu statik tarama hukuki menşe sertifikası değildir; bulunmayan metadata'yı otomatik olarak doğrulanmış saymaz. UNVERIFIED öğeleri insan incelemesi gerektirir.

## Bugünkü durum

Aşağıdaki başlıklar çözülmeden “%100 yerli” veya “tam egemen” ifadesi kullanılmamalıdır: gerçek onaylı eğitim korpusu, yeterli sıfırdan eğitim koşusu, insan puanlamalı Türkçe kalite raporu, kendi checkpoint'imizin HTTP servisinde uçtan uca kullanımı, tam transitif bağımlılık/lisans envanteri, ağsız tekrarlanabilir derleme, gerçek donanım ölçümleri, ortak kalıcı dağıtık durum ve üretim seviyesinde mTLS/iptal/çok düğümlü testleri.

Her kapının tamamlanması, kanıt artefaktı ve bağımsız incelemeyle işaretlenir. Plan maddesini eklemek veya CI'ın geçmesi tek başına kapıyı kapatmaz.

## 2026-10-16 — SBOM üretimi ve provenance attestation
- [x] tools/generate_mkaos_sbom.py kurulu Python çalışma ortamı için CycloneDX 1.5 SBOM üretir; eksik lisans metaverisini tahmin etmez ve raporu INCOMPLETE_REQUIRES_HUMAN_REVIEW olarak işaretler.
- [x] Güvenilir main/workflow_dispatch CI çalıştırmalarında SBOM artefaktı üretmek ve GitHub provenance attestation yayımlamak için ayrı iş eklendi; PR kodundan attestation üretilmez.
- [ ] Bu, bağımlılıkların lisanslarının hukuken temizlendiği anlamına gelmez. Tam transitif lisans incelemesi, kaynak hash/provenance doğrulaması, ağsız tekrarlanabilir build ve dağıtılan container imajı için ayrıca imzalı provenance doğrulaması hâlâ gereklidir.