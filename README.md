# MKAOS — Sentinel Agent Intelligence

<div align="center">
<img src="web/static/mkaos-emblem.svg" alt="MKAOS silver and violet official wordmark" width="320" />

**Türkiye'den doğan, yerel öncelikli yapay zekâ platformu**

*Bugünün güvenilir altyapısını kurarken yarının kendi temel modelini geliştirmek.*
</div>

[CI](https://github.com/Nexora88/sentinel-agent/actions) · [Lisans](LICENSE) · [Sorun bildir](https://github.com/Nexora88/sentinel-agent/issues)

---

## Türkçe

MKAOS; yerel çalışmayı, denetlenebilir araçları, kullanıcı denetimini ve bilimsel dürüstlüğü önceleyen bir yapay zekâ platformu projesidir. Python tabanlı uygulama katmanı, deneysel Rust çıkarım bileşenleri, yerel bilgi erişimi ve sınırlandırılmış araç entegrasyonları içerir.

### Vizyonumuz

Uzun vadeli hedefimiz, izinleri ve menşei belgelenmiş Türkçe veriler, şeffaf eğitim süreçleri, tekrarlanabilir deneyler ve bağımsız kalite ölçümleriyle **kendi temel modelimizi sıfırdan geliştirmek**; bir gün gerçekten Türkiye'de üretilmiş, teknik kökeni kanıtlanabilir bir model ortaya koymaktır.

Bu bir vizyondur, tamamlanmış başarı iddiası değildir. “Yerli” niteliği yalnızca marka veya arayüzle ölçülmez; veri, eğitim, ağırlıklar, yazılım, donanım ve tedarik zinciri ayrı ayrı belgelenmelidir. Atatürk'ün akıl ve bilim yaklaşımını, Türkçe teknoloji üretimini ve açık kaynak iş birliğini temel alıyoruz.

### Gerçek durum — 23 Ekim 2026

- **Kendi temel modelimiz:** Henüz onaylanmış eğitim korpusu ve kullanılabilir, eğitilmiş MKAOS checkpoint'i yok. Bağımsız Türkçe kalite skoru da yayımlanmış değil.
- **Sohbet neden 503 döndürüyor?** Varsayılan sohbet yolu yerel MKAOS HTTP çıkarım sunucusuna bağlanır. Sunucu kapalıysa, model dosyası yoksa veya uyumlu model yüklenmemişse API 503 döndürür. Alternatif `native-rust` yolu ayrıca yapılandırılmış checkpoint ve SHA-256 gerektirir. Bu davranış kullanıcıya hatanın nedenini görünür kılar; uyumlu yerel model sunucusu çalıştırılmadan soru-cevap üretilemez.
- **CI'da model deneyi:** Ayrı bir GitHub Actions işi, sabitlenmiş üçüncü taraf SmolLM2-135M-Instruct modelinin dosya hash'lerini, tokenizer/runtime uyumunu ve internet erişimi kapatıldıktan sonra gerçek Türkçe isteme yanıt üretmesini doğrular. Ölçümler GitHub'ın geçici CPU çalıştırıcısına aittir; MKAOS'un kendi modeli veya kullanıcının bilgisayarı için performans kanıtı değildir. Yalnızca rapor artifact'i saklanır; ağırlıklar repoya eklenmez.
- **Yerel Rust motoru:** Deneysel hesaplama/çıkarım altyapısı vardır; SmolLM2 gibi bir modelin mimarisi ve tokenizer'ıyla uyumlu, üretime hazır genel amaçlı motor olduğu varsayılmamalıdır.
- **Crypto-RAG:** AES-GCM şifreli SQLite depo ve kontrollü aktarım yardımcıları bulunur. Kullanıcının gerçek deposunda doğrulanmış, uçtan uca geri yükleme provası ayrıca yapılmalıdır.
- **Ajan ağı:** mTLS yardımcıları ve WireGuard yönergeleri vardır; gerçek makinelerde sertifika dağıtımı/iptali ve ağ topolojisi doğrulanmadan üretime hazır sayılmaz.
- **Kuantum sonrası güvenlik:** ML-KEM, ML-DSA veya hibrit TLS üretim için etkinleştirilmiş ve birlikte çalışabilirliği kanıtlanmış değildir.
- **Operasyon:** Bir CI işinin geçmesi bütün CI, dağıtım, donanım veya güvenlik kontrollerinin geçtiği anlamına gelmez.

### Mevcut altyapı

- Python API ve ajan orkestrasyonu; insan onayına bağlı işlemler.
- Deneysel Rust CPU çıkarım motoru, model manifesti ve SHA-256 bütünlük kontrolleri.
- Yerel RAG ve isteğe bağlı şifreli SQLite vektör deposu.
- Sınırlandırılmış, salt okunur MCP sunucu temeli.
- Yerel test hedefleri için izole tarayıcı laboratuvarı.
- Ağ, model, veri ve güvenlik durumları için yapılandırma ve denetim yardımcıları.

Bunlar tek başına üretim güvenliği, doğru Türkçe cevaplar, tam egemenlik veya kuantum güvenliği sertifikası değildir.

### Başlangıç

Gereksinimler: Python 3.12. Model dosyaları kaynak depoya dahil değildir.

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
# .env.example dosyasını .env olarak kopyala ve güçlü OWNER_PASSWORD ayarla
python -m scripts.run web --host 127.0.0.1 --port 8000
```

Arayüz: http://127.0.0.1:8000

**Not:** Bu komutlar web uygulamasını başlatır; model ağırlıklarını veya uyumlu sohbet motorunu otomatik kurmaz. Sohbetin çalışması için checkpoint, hash ve doğru yerel çalıştırıcı ayrıca yapılandırılmalıdır. Sadece arayüzün açılması modelin hazır olduğu anlamına gelmez.

### Doğrulama komutları

```bash
python -m unittest discover -s tests -v
node --check web/static/app.js
python -m scripts.run secrets --path .
python -m scripts.run licenses --path .
```

Her test sonucu yalnızca çalıştırıldığı commit ve kapsam için geçerlidir. TTFT, token/s veya Türkçe kalite iddiaları checkpoint, tokenizer, donanım, test kümesi ve ölçüm yöntemiyle birlikte yayımlanmalıdır.

### Yol haritası — kanıt kapıları

1. **Kullanılabilir yerel sohbet:** Seçilen checkpoint ve tokenizer ile uyumlu runtime; Türkçe soru-cevap regresyon testleri; anlaşılır kurulum ve hata durumu.
2. **Veri yönetişimi:** Lisans/izin/mahremiyet incelemesi tamamlanmış korpus, sürümlü manifest ve ayrı tutulan test kümesi.
3. **Tekrarlanabilir model değerlendirmesi:** Sabit checkpoint ve donanımla TTFT, token/s, bellek ve bağımsız Türkçe benchmark.
4. **Crypto-RAG dayanıklılığı:** Gerçek test verisiyle şifreleme, taşıma, yedekleme, geri yükleme ve bütünlük karşılaştırması.
5. **Ajan ağı:** Ayrı test makinelerinde WireGuard, mTLS kimlik dağıtımı, yenileme/iptal ve ağ kesintisi testleri.
6. **Kuantum sonrası kriptografi:** Sürümleri sabitlenmiş uygulama, hibrit geçiş tasarımı, bilinen test vektörleri ve bağımsız birlikte çalışabilirlik denemeleri.
7. **Operasyonel güvence:** Zorunlu CI işleri, bağımlılık ve sır taramaları, dağıtım smoke testleri, geri alma ve yedek geri yükleme provası.

Hiçbir kilometre taşı yalnızca belge eklenmesiyle tamamlanmış sayılmaz; test çıktısı ve kapsamı gerekir.

### Veri ve güvenlik ilkeleri

- Kullanım hakkı açık olmayan veri eğitimde kullanılmaz.
- Model ağırlıkları, kişisel veriler, token'lar ve özel anahtarlar Git'e eklenmez.
- Şifreli depoya geçiş, yedek ve geri yükleme doğrulanmadan eski veriyi silmez.
- Yerel uygulama ayarları tek başına ağ çıkışını engellemez; gerekiyorsa işletim sistemi güvenlik duvarı ile doğrula.
- İnsan onayı gerektiren dış etkiler otomatikleştirilmez.
- Üçüncü taraf model kullanımı varsa sağlayıcı, lisans ve veri akışı açıkça belirtilir.

### Belgeler

- [Marka kimliği ve vizyon](docs/MKAOS_BRAND_AND_VISION.md)
- [Bağımsızlık kilometre taşları](docs/MKAOS_INDEPENDENCE_MILESTONES.md)
- [Türkçe veri yönetişimi](docs/MKAOS_TURKISH_DATA_GOVERNANCE.md)
- [Ağ gizliliği](docs/NETWORK_PRIVACY.md)
- [Yerel semantik RAG kurulumu](docs/MKAOS_RAG_SEMANTIC_SETUP.md)
- [Açık kaynak hazırlık durumu](docs/MKAOS_OPEN_SOURCE_READINESS.md)

---

## English

MKAOS is a Turkey-originated, local-first AI platform project focused on auditable tools, user control, and scientific honesty. Its long-term vision is to develop a genuinely domestically produced foundation model from scratch using permission-cleared data, reproducible training, transparent provenance, and independent evaluation.

This is a goal, not a claim of present-day model independence. The repository currently has no approved training corpus, usable MKAOS-trained checkpoint, or independently validated Turkish quality score.

### Current evidence and limitations

- The default chat path connects to the local MKAOS HTTP inference server. If the server is stopped, the model files are missing, or no compatible model is loaded, the API returns HTTP 503. The optional native-rust CLI path separately requires a configured checkpoint and SHA-256. This is an explicit local runtime requirement, not a claim that model-backed chat works without a model.
- A separate GitHub Actions test validates a pinned third-party SmolLM2 reference model, its hashes and tokenizer/runtime compatibility, and Turkish prompt generation after network access is disabled. Those are hosted-runner measurements, not performance results for a user's computer or a MKAOS-trained model.
- The Rust runtime is experimental and must not be assumed compatible with arbitrary model architectures or tokenizers.
- Crypto-RAG migration/restore, real-host WireGuard and mTLS lifecycle, production post-quantum cryptography, and full deployment operations require additional end-to-end verification.
- A passing CI job proves only the checks in that job and commit.

### Quick start

Requires Python 3.12. Model weights are not bundled.

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m scripts.run web --host 127.0.0.1 --port 8000
```

This starts the web application only. A separate local inference server and its compatible model files are also required. The repository does not automatically download model weights. The SmolLM2 compatibility server is a third-party reference runtime, not a MKAOS-trained model.

### Validation

```bash
python -m unittest discover -s tests -v
node --check web/static/app.js
python -m scripts.run secrets --path .
python -m scripts.run licenses --path .
```

Report latency, throughput, memory, or language-quality claims only with the exact checkpoint, tokenizer, hardware, test set, and procedure.

### Principles

- No dataset is used for training without documented rights and privacy review.
- Never commit weights, secrets, private keys, or personal datasets.
- Never delete source data before a backup restore and integrity check succeeds.
- Local application settings alone do not guarantee network isolation.
- Third-party model usage and data flows must be explicit.
- See the Turkish documentation links above for the full roadmap and policies.

## License

The repository declares MIT licensing. Third-party code, weights, datasets, voices, and artwork may have separate terms.