<div align="center">

<img src="web/static/mkaos-emblem.svg" alt="MKAOS silver and violet emblem" width="120" />

# MKAOS — Sentinel Agent Intelligence

**Yerel öncelikli ajan platformu · Local-first agent platform**

[![CI](https://github.com/Nexora88/sentinel-agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Nexora88/sentinel-agent/actions) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[Türkçe](#türkçe) · [English](#english) · [Issues](https://github.com/Nexora88/sentinel-agent/issues)

</div>

## Türkçe

MKAOS; Python ve Rust ile geliştirilen, **yerel çalışmayı, denetlenebilir araçları ve insan onayını** önceleyen deneysel bir ajan platformudur. Görev yönetimi, yerel bilgi erişimi, araç sınırları ve bağımsız çıkarım altyapısı üzerinde çalışır.

> **Gerçek durum:** MKAOS bugün “%100 yerli”, bağımsız bir temel model veya üretime hazır kuantum güvenli ajan ağı değildir. Onaylanmış, kullanılabilir bir MKAOS dil modeli checkpoint’i ve bağımsız Türkçe kalite skoru henüz mevcut değildir. Checkpoint yokken sohbet uç noktası kasıtlı olarak HTTP 503 verir; bu güvenli hata davranışıdır, çalışan genel amaçlı modelin kanıtı değildir.

### Mevcut yetenekler

- **Python + Rust çıkarım iskeleti:** CPU decoder/KV-cache geliştirme ve yerel CLI adaptörü; kullanılabilir model ağırlıkları ayrıca gerekir.
- **Yerel RAG:** Yerel semantik embedding modeline dayalı bilgi erişimi; model ve SHA-256 envanteri önceden sağlanmalıdır.
- **MCP:** Kısıtlı, salt okunur stdio sunucu temeli; genel shell veya sınırsız dosya erişimi sunmaz.
- **Crypto-RAG:** İsteğe bağlı AES-GCM şifreli SQLite vektör deposu ve kontrollü aktarım/doğrulama; eski depo otomatik silinmez.
- **İzole tarayıcı laboratuvarı:** İzinli yerel test hedefinde Playwright ekran görüntüsü; canlı tarama varsayılan olarak açık değildir.
- **Ajan ağı/PQC hazırlığı:** mTLS yardımcıları ve WireGuard yönergeleri; gerçek makinelerde ağ kurulumu ve üretim PQC tamamlanmış değildir.
- **Arayüz:** Gümüş-mor amblem ve koyu obsidyen/mor tema.

### Eksikler ve ölçüm durumu

- Onaylanmış yerel MKAOS model ağırlıkları ve güvenilir Türkçe benchmark.
- Checkpoint ve donanım belirtilerek tekrarlanabilir TTFT, token/s ve bellek ölçümleri.
- Gerçek veriyle doğrulanmış Crypto-RAG aktarımı ve geri yükleme testi.
- Gerçek makinelerde doğrulanmış WireGuard, mTLS sertifika dağıtımı ve iptal süreçleri.
- ML-KEM/ML-DSA veya hibrit TLS için sabitlenmiş uygulama ve birlikte çalışabilirlik testleri.
- Tüm CI işleri ve dağıtım için bağımsız operasyonel doğrulama.

### Hızlı başlangıç

Gereksinimler: Python 3.12; model ağırlıkları ve embedding modeli ayrıca sağlanır.

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

`.env` içinde güçlü ve benzersiz `OWNER_PASSWORD` belirle. Yerel geliştirme sunucusu:

```bash
python -m scripts.run web --host 127.0.0.1 --port 8000
```

[http://127.0.0.1:8000](http://127.0.0.1:8000) adresini aç. Checkpoint yoksa sohbetin 503 dönmesi beklenir. Geliştirme ayarlarını internete açık sunma.

### Testler

```bash
python -m unittest discover -s tests -v
node --check web/static/app.js
```

CI yalnızca GitHub Actions’ta listelenen commit ve işler için geçerlidir. Atlanan eğitim işi başarılı eğitim sayılmaz. TTFT, token/s veya Türkçe kalite iddiaları için checkpoint, donanım, test kümesi ve yöntem yayımlanmalıdır.

### Güvenli veri aktarımı

1. Kaynak depoyu yedekle ve geri yüklemeyi doğrula.
2. Aktarımı ayrı bir hedef depoya yap.
3. Kayıt sayısı, içerik, embedding ve bütünlük özetlerini karşılaştır.
4. Eski düz metin depoyu doğrulanmış yedek ve açık sahip onayı olmadan silme.
5. Anahtarları, token’ları veya özel verileri Git’e ekleme.

---

## English

MKAOS is an experimental Python/Rust agent platform focused on **local-first operation, auditable tools, and human approval**. It explores task orchestration, local retrieval, bounded tool access, and an independent inference runtime.

> **Honest status:** MKAOS should not currently be described as “100% domestic,” a fully independent foundation model, or a production-ready quantum-secure agent network. There is no approved, usable MKAOS language-model checkpoint or independently validated Turkish quality score yet. Without a checkpoint, the chat endpoint intentionally returns HTTP 503. This is fail-closed behavior, not evidence of a working general-purpose model.

### Available foundations

- **Python + Rust inference scaffolding:** CPU decoder/KV-cache development and local CLI adapter; usable weights are separate.
- **Local RAG:** Retrieval using a locally provisioned semantic embedding model and verified SHA-256 inventory.
- **MCP:** Bounded, read-only stdio server foundation; no unrestricted shell or filesystem access.
- **Crypto-RAG:** Opt-in AES-GCM encrypted SQLite vector store and controlled migration/verification; source data is not automatically deleted.
- **Isolated browser lab:** Playwright screenshots against an allowlisted local test target; live scanning is not enabled by default.
- **Agent mesh/PQC preparation:** mTLS policy helpers and WireGuard guidance; production deployment and PQC are not complete.
- **UI:** Silver/violet emblem and dark obsidian/violet theme.

### Known gaps

- Approved local MKAOS model weights and a reliable Turkish-language benchmark.
- Reproducible TTFT, tokens/second, and memory measurements tied to a named checkpoint and hardware.
- A Crypto-RAG migration with verified backup and restore.
- Verified WireGuard deployment, mTLS certificate distribution, and revocation operations on real hosts.
- Pinned ML-KEM/ML-DSA or hybrid-TLS implementation with interoperability and key-lifecycle tests.
- Independent operational verification of all CI jobs and live deployment.

### Quick start

Requirements: Python 3.12. Model weights and the embedding model must be provisioned separately.

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Set a strong, unique `OWNER_PASSWORD` in `.env`. Start the local development server:

```bash
python -m scripts.run web --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). HTTP 503 is expected when no model checkpoint is configured. Do not expose development defaults to the public internet.

### Tests

```bash
python -m unittest discover -s tests -v
node --check web/static/app.js
```

CI results apply only to the commit and jobs shown in GitHub Actions. A skipped training job is not a successful training run. TTFT, tokens/second, and Turkish-quality claims require the checkpoint, hardware, dataset, and measurement procedure to be reported.

### Safe data migration

1. Back up the source store and verify a restore.
2. Migrate into a separate destination.
3. Compare record counts, content, embeddings, and integrity hashes.
4. Keep plaintext source data until backup verification and explicit owner approval.
5. Never commit secrets or private data.

## Architecture / Mimari

- **Python:** orchestration, APIs, tools, and security policy.
- **Rust:** experimental local inference runtime.
- **RAG:** local retrieval with separately provisioned model assets.
- **Security:** opt-in encrypted storage and bounded tool interfaces; production use requires additional validation.

## Documentation / Belgeler

- [Open-source readiness](docs/MKAOS_OPEN_SOURCE_READINESS.md)
- [Independence milestones](docs/MKAOS_INDEPENDENCE_MILESTONES.md)
- [Turkish data governance](docs/MKAOS_TURKISH_DATA_GOVERNANCE.md)
- [Network privacy guide](docs/NETWORK_PRIVACY.md)
- [Semantic RAG setup](docs/MKAOS_RAG_SEMANTIC_SETUP.md)

## Contributing / Katkıda bulunma

Reproducible bug reports, tests, documentation, and focused pull requests are welcome. Include reproduction steps; never include credentials or private data. Check the license and usage terms for each third-party dependency, model, dataset, and artwork.

## License / Lisans

The repository declares MIT licensing. Third-party code, model weights, datasets, and artwork may carry separate terms. Public availability does not automatically permit model training or redistribution.

---
# MKAOS v6.5 — Mustafa Kemal Atatürk Operating System

**MKAOS, bağımsız bir proje ve marka adıdır.** Teknik sınıflandırma açısından mevcut sürüm bir Linux dağıtımı veya işletim sistemi çekirdeği değil; Python/Rust tabanlı, yerel çalışmayı ve insan onayını esas alan ajan, çıkarım, bilgi erişimi ve görev yönetimi platformudur. “Operating System” adı ürün vizyonunu/markasını ifade eder; kernel veya Linux dağıtımı olduğu iddiası değildir.

**Yerel Türkçe ajan platformu.** HTTP sohbet yolu artık varsayılan olarak yerel Rust `mkaos-generate` CLI'ına gider ve onaylı yerel checkpoint yoksa açıkça `503` döndürür; üçüncü taraf SmolLM2'ye sessiz geri dönüş yapılmaz. Ancak henüz onaylı Türkçe korpus, eğitilmiş kullanılabilir MKAOS checkpoint'i veya bağımsız Türkçe kalite kanıtı yoktur. Sentetik CI eğitimi mimari/aktarım testidir; gerçek Türkçe yetenek kanıtı değildir. Güvenlik, veri sahipliği ve insan onayı temel ilkedir.

MKAOS; görev planlama, yerel bilgi deposu, kod inceleme, savunmacı güvenlik taraması, iş kuyruğu ve isteğe bağlı GitHub araçlarını bir araya getirir. POST /api/chat varsayılan olarak yerel Rust CLI yolunu kullanır ve model dosyası yoksa hata görünür kalır. RAG varsayılanı, önceden yerel diske kurulmuş çok dilli semantik embedding modelidir; çalışma sırasında internetten model indirilmez. Model bulunmaz veya SHA-256 envanteri uyuşmazsa semantik RAG başlatılması hata verir; sessizce n-gram veya bulut sağlayıcısına düşmez. N-gram yalnızca açıkça seçilebilen deneysel baseline olarak kalır.

## Bağımsız çıkarım motoru — aşamalı geçiş

- Çekirdek: [engine/mkaos-inference/](engine/mkaos-inference/) — Rust CPU tensör işlemleri, Transformer decoder ve KV cache.
- Eğitim: tools/train_mkaos_from_scratch.py rastgele başlatılmış ağırlıklarla eğitim altyapısı sağlar; yalnızca onaylı yerel korpus ve manifest kabul edilir.
- HTTP sohbet adaptörü: core/mkaos_native_chat.py yerel mkaos-generate ikilisini shell kullanmadan çalıştırır; hash, boyut, zaman aşımı ve çıktı sınırlarını denetler.
- Docker imajı Rust CLI'ı çok aşamalı derlemeyle paketler. Model ağırlıkları otomatik indirilmez ve depoya dahil edilmez.
- Şimdilik onaylı Türkçe korpus veya eğitilmiş kullanılabilir checkpoint yoktur. Bu nedenle varsayılan sohbet, checkpoint yapılandırılana kadar açık HTTP 503 döndürür; üçüncü taraf modele sessiz geri dönüş yoktur.
- Üçüncü taraf SmolLM2 uyumluluk servisi yalnızca açıkça seçilen legacy-third-party-chat Compose profili ile başlatılabilir.
- RAG varsayılanı, `models/embeddings/paraphrase-multilingual-MiniLM-L12-v2/` altındaki önceden kurulmuş yerel semantik embedding modelidir. Model ağırlıkları depoya eklenmez veya çalışma anında indirilmez; hazırlık adımları için [yerel semantik RAG kurulumu](docs/MKAOS_RAG_SEMANTIC_SETUP.md) belgesine bak.

### Başlatma

1. `.env.example` dosyasını `.env` olarak kopyala.
2. Yerel semantik RAG modelini ve SHA-256 envanterini [kurulum belgesindeki](docs/MKAOS_RAG_SEMANTIC_SETUP.md) adımlarla `models/embeddings/` altına yerleştir. Model yoksa uygulama sessizce n-gram/uzak modele dönmez.
3. Onaylı korpusla eğitim ve bağımsız inceleme tamamlandıktan sonra checkpoint'i models/mkaos/model.mkaosw içine yerleştir; eğitim raporundaki SHA-256 değerini MKAOS_NATIVE_SHA256 olarak ayarla. Heads/KV-heads/sequence ayarları checkpoint mimarisiyle eşleşmelidir.
4. `docker compose up --build` komutuyla başlat. Checkpoint yokken sohbetin 503 dönmesi beklenen fail-closed davranışıdır.

Yol haritası: [docs/MKAOS_INDEPENDENCE_MILESTONES.md](docs/MKAOS_INDEPENDENCE_MILESTONES.md). Günlük kalite döngüsü, çevrimdışı dayanıklılık ve donanım sürümleri: [MKAOS_DAILY_IMPROVEMENT_AND_EDITIONS.md](docs/MKAOS_DAILY_IMPROVEMENT_AND_EDITIONS.md).

10B sıfırdan eğitim profili yalnızca engelli bir kapasite planıdır; yakın vadeli hedef değildir. Önce küçük model/boru hattı deneyleri ve bağımsız kalite ölçümleri; ihtiyaç ve lisans elverirse sabitlenmiş açık ağırlıklı bir temel model üzerinde LoRA/PEFT denemeleri değerlendirilir. Bu tür bir adaptör, sıfırdan eğitilmiş MKAOS ağırlıkları olarak sunulmaz. 10B hedefi ve bulut eğitimine hazır olma kapıları: [docs/MKAOS_10B_SCALE_UP_GATES.md](docs/MKAOS_10B_SCALE_UP_GATES.md). Tam parametre sayımlı profil [configs/mkaos/train-10b.json](configs/mkaos/train-10b.json) içindedir; planlama için kilitli ve eğitime kapalıdır. Önceki 50B ve 90B belgeleri tarihsel yol haritasıdır.

## Native Rust chat integration status

- `POST /api/chat` defaults to `MKAOS_CHAT_BACKEND=native-rust` and invokes the locally packaged Rust CLI without a shell.
- The checkpoint must be supplied locally at `models/mkaos/model.mkaosw` and its SHA-256 set through `MKAOS_NATIVE_SHA256`; the repository intentionally does not bundle model weights.
- Until an approved corpus produces a real checkpoint, chat returns HTTP 503. It does not silently use third-party weights.
- The third-party SmolLM2 compatibility service is gated behind the explicit `legacy-third-party-chat` Compose profile.
- This wiring is not proof of useful Turkish quality, production performance, full supply-chain independence, or completed hardware/distributed validation.

## Marka ve tasarım ilkesi

MKAOS, *Mustafa Kemal Atatürk Operating System* anlamıyla yerel egemenlik, bilim ve üretim hedefini temsil eder. Arayüz sloganı: **“İstikbal Siber Göklerdedir.”** Marka veya ağ durumu tek başına güvenlik kanıtı değildir; “TAM EGEMEN / AIR-GAPPED” yalnızca ağ çıkışı gerçekten sınırlandırılıp doğrulandığında kullanılmalıdır.

## Gizlilik modeli ve sınırlar

- **Yerel çıkarım:** Varsayılan sohbet motoru yerel Rust CLI'dır; ancak onaylı/eğitilmiş checkpoint henüz sağlanmadığı için chat varsayılan kurulumda 503 verir. Eski Ollama/üçüncü taraf model kullanımı yalnızca açıkça seçilen uyumluluk yollarıyla yapılmalıdır. RAG'in yerel n-gram baseline'ı eğitilmiş semantik model değildir.
- **Yerel saklama:** kullanıcıya göre ayrılmış sohbet geçmişi ve onay günlüğü atomik dosya yazımıyla yerel `memory/` içinde tutulur; bozuk veri sessizce sıfırlanmaz. Bellek ve vektör deposu da yerel proje/volume içindedir. Bu dizini şifreli disk üzerinde tut ve yedekle.
- **Web araştırması kapalı başlar:** `ALLOW_WEB_RESEARCH=false` iken bilgi genişletme arama sorgusu göndermez. Bilerek açarsan arama sorguları ve sayfa istekleri internete çıkar. `ALLOW_EXTERNAL_FINANCE_DATA=false` canlı hisse/kripto fiyatlarını ve paper motorunun fiyat isteklerini de kapatır; `ALLOW_SITE_SCANNING=false` site taramasını kapatır. Bunları açmak ilgili sorgu/hedef bilgilerini dış servislere gönderir. GitHub token'ı GitHub'a istek gönderir. Üçüncü taraf bildirimleri `ALLOW_EXTERNAL_NOTIFICATIONS=true` ile açıkça etkinleştirilmedikçe kapalıdır. Tam çevrimdışı kullanım için bu özellikleri çalıştırma, kimlik bilgilerini tanımlama ve ağ çıkışını işletim sistemi/firewall seviyesinde kısıtla.
- **Onay varsayılanı açık:** GitHub yazma, commit, push ve dosya değişiklikleri otomatik yapılmamalıdır. Her onay kararlı bir istek kimliğine bağlıdır.
- **Savunmacı tarama:** web tarayıcısı yerel/özel IP'leri ve doğrulanmayan yönlendirmeleri engeller. Yalnızca sahibi olduğun veya tarama iznin olan hedeflerde kullan.
- **Güvenlik dürüstlüğü:** uygulama tek başına “veri asla dışarı çıkamaz” garantisi veremez. Bu; uygulama ayarlarına, işletim sistemi/firewall'a, model endpoint'ine, yedeklemeye ve etkinleştirilen entegrasyonlara bağlıdır.

## Egemenlik, imzalı onay ve yerel hafıza

- `GET /api/sovereignty` ağ bağlantısı denemesi yapmadan bulut işaretlerini ve opsiyonel host attestasyon dosyasını okur. Sonuç tek başına firewall denetimi değildir; uygulama `fully_sovereign=false` döndürür.
- `POST /api/approval/verify` Ed25519 imzasını doğrular, payload hash'ini yerel audit dosyasına yazar ve tekrar kullanılan `request_id` değerini reddeder. Bu sürüm doğrulama sonrasında otomatik push/merge yürütmez.
- Tarayıcıdaki anahtar üretimi özel anahtarı indirir; özel anahtar MKAOS sunucusuna gönderilmez. Açık anahtar `MKAOS_APPROVAL_ED25519_PUBLIC_KEY` ortam değişkenine eklenmelidir.
- `GET /api/audit/clean-room` SPDX/lisans bildirim ipuçlarını tarar. Semantik benzerlik taraması yapmaz ve telif temizliği garantisi değildir.
- `POST /api/privacy/forget` yalnızca açık `DELETE_MATCHING_MEMORY` onayıyla çalışır; zaman damgalı kişisel vektör kayıtları ve zaman damgalı sohbet eşleşmelerini siler. Zaman damgası olmayan eski sohbetler/profil gerçekleri, yedekler ve sistem günlükleri korunur.

## Yerel medya stüdyosu

- Görsel üretimi ve düzenleme yalnızca `SD_API_URL` ile açıkça yapılandırılmış, kendi yönettiğin Stable Diffusion WebUI API sunucusuna gider. Kamuya açık görsel API yedeği kaldırılmıştır; sunucu tanımlı değilse işlem başarısız olur ve görsel istemi dışarı gönderilmez.
- `POST /api/media/edit` yerel `img2img` uç noktasını kullanır. `POST /api/media/background` isteğe bağlı `rembg` + önceden indirilmiş `u2net.onnx` modeliyle arka planı ayırıp yerel renk ile birleştirir. İlk çalıştırmada otomatik model indirme yapılmaz. Arka plan özelliğinin Python bağımlılığı için `pip install -r requirements-media.txt` kullan; `u2net.onnx` dosyasını güvenilir kaynaktan önceden indirip `U2NET_HOME` içine yerleştir.
- `POST /api/media/video` yerel `ffmpeg` ile mevcut PNG görseline kısa hareket/zoom efekti verir. `POST /api/media/story-video` ise 2-6 sahne açıklamasından, açıkça yapılandırılmış yerel Stable Diffusion modelinde ayrı anahtar kareler üretir ve bunları yerel `ffmpeg` ile MP4 olarak birleştirir. Bu, çok sahneli AI storyboard videosudur; **nöral text-to-video modeli değildir**. İstek gövdesi: `{"prompts":["Sahne 1 açıklaması","Sahne 2 açıklaması"],"duration":8}`; süre 4-24 saniye ile sınırlandırılır. Ağ çıkışı veya bulut medya API'si yedeği yoktur.
- Görseller 12 MB ve 20 MP sınırlarıyla doğrulanır; çıktılar yerel `memory/generated_images/` içinde tutulur. `SD_API_URL` boşsa üretim kapalıdır.

## Şifreli yerel bellek ve Passkey

- `MKAOS_ENCRYPT_MEMORY_FILES=true` kişisel profil, sohbet geçmişi ve kullanıcı hesap deposunu `MKAOS_MEMORY_KEY` ile AES-256-GCM şifreli dosyalara taşır. `MKAOS_ENCRYPT_PERSONAL_PROFILE=true` yalnızca kişisel profili şifreler.
- Anahtar 32 bayt rastgele veri olmalı ve Base64 olarak veri dizini/depo dışında sağlanmalıdır. Anahtar kaybında şifreli veriler kurtarılamaz.
- Eski düz metin dosyalar otomatik taşınmaz; açık ve gözden geçirilmiş geçiş gerekir. Chroma/RAG vektörleri, yüklemeler, üretilen medya, günlükler, yedekler ve diğer dosyalar bu ayarla şifrelenmez. Tüm disk/hacim için işletim sistemi veya depolama katmanı şifrelemesi ayrıca gerekir.
- WebAuthn/passkey rotaları: `/api/webauthn/register/options`, `/api/webauthn/register/verify`, `/api/webauthn/login/options`, `/api/webauthn/login/verify`. Arayüz parola ile girişten sonra kenar menüsünden passkey kaydı ve giriş ekranından passkey ile oturum açma sağlar.
- HTTPS, localhost dışındaki isteklere varsayılan olarak zorunlu uygulanır. Üretimde `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGIN`, `REQUIRE_HTTPS=true` değerlerini gerçek HTTPS alan adına göre ayarla; ters vekil arkasında `TRUST_PROXY_HEADERS=true` yalnızca güvenilir proxy başlıkları yeniden yazıyorsa kullanılmalıdır. `TRUST_PROXY_HEADERS=true` yalnızca gelen forwarded başlıklarını silip yeniden yazan güvenilir bir ters vekil varsa kullanılmalıdır.
- Uygulama HTTPS ve güvenlik başlıklarını ayarlayabilir; ana bilgisayar güvenlik duvarı, TLS sertifikası, yedekler ve fiziksel cihaz doğrulaması yine dağıtım düzeyinde yapılmalıdır.

## Yerel akıl yürütme, donanım ve ajan kümesi

- `core/reasoning_engine.py): Yerel modeller arasında taslak → eleştiri → sonuç görev yönlendirmesi (isteğe bağlı farklı modeller). Gizli düşünce zincirini döndürmez; kısa değerlendirme, belirsizlik ve sonraki adımlar verir. Araç çalıştırmaz, dosya değiştirmez ve PR birleştirmez.
- `core/hardware_backends.py): CPU, NVIDIA CUDA, AMD ROCm, Apple Metal, Intel Gaudi ve NPU/TPU için dürüst yetenek kaydı. CUDA/ROCm/Metal/Gaudi/NPU desteği donanımda doğrulanana kadar “doğrulanmadı” olarak kalır.
- `core/agent_mesh.py): Ed25519 imzalı, süre ve boyut sınırı olan, tekrar oynatma korumalı veri görevleri. Bu modül ağ taşıması, şifreleme veya uzaktan kod çalıştırma sağlamaz; gerçek mesh için mTLS, anahtar iptali ve açık eş listesi gerekir.
- `scripts/benchmark_local_reasoning.py): Türkçe kalite görevlerini yerel Ollama modelinde çalıştırıp süre ve yanıtları yerel rapora yazar.

Yerel değerlendirme örneği:

```bash
python scripts/benchmark_local_reasoning.py --model qwen2.5:7b --output memory/benchmarks/qwen25-7b.json
```

Rapor otomatik kalite sertifikası değildir; yanıtları beklenen kontrol maddelerine göre incele. Model ailesi eğitimi, gerçek MoE mimarisi, GPU hızlandırıcıların cihaz üstü doğrulaması, FHE ve canlı P2P taşıması henüz bu PR ile tamamlanmış sayılmaz.

Kubernetes için başlangıç dosyaları `deploy/kubernetes/` altındadır. Dağıtım tek replika ile sınırlıdır; uygulama oturumları, WebAuthn challenge'ları ve yerel PVC henüz yatay ölçekli ortak veri katmanı değildir. İmaj özeti, şifreli depolama, gerçek ingress/TLS, CNI NetworkPolicy ve mTLS dağıtım öncesi ayrıca doğrulanmalıdır.

Ayrıntılı mimari, model eğitimi ve sertifikasyon sınırları: `docs/REASONING_MESH_ACCELERATION.md`.

## Denetlenebilir kod geliştirme

Gece araştırmacısı kaynakları ve kodu analiz edip öneriler üretir; `POST /api/improvements/generate` yerel kod modelinden izin verilen mevcut bir dosya için birleşik diff taslağı oluşturur. `POST /api/improvements/proposals` ise elle hazırlanmış önerileri de kabul ederek kullanıcı başına ayrı depoda dosyaları, yama metnini ve test planını saklar. Öneri listesi ve yama yalnızca kimliği doğrulanmış aynı kullanıcı tarafından okunabilir. `READY_FOR_HUMAN_CODE_REVIEW` onayı sadece öneriyi insan incelemesine hazır olarak işaretler; dosya değiştirmez, kod çalıştırmaz, commit/push/merge veya dağıtım yapmaz. Hedefler `agents/`, `core/`, `tools/`, `web/`, `tests/`, `docs/` ve `config/` ile sınırlıdır; yol geçişi ve sır dosyaları reddedilir. Önerilen yamalar ayrıca CI, güvenlik taraması ve insan incelemesinden geçmelidir.

## Kesin çevrimdışı çalışma profili

`docker-compose.yml` varsayılan olarak MKAOS ve Ollama'yı internet çıkışı olmayan `seka_isolated` Docker ağına bağlar. `docker-compose.offline.yml` bu tercihi ayrıca açıkça belirtir. GitHub token'ı, web araştırması, dış bildirim ve harici görsel üretimi bu profilde kapalıdır. Bu nedenle canlı finans verisi, GitHub yazma ve web taraması çevrimdışı profilde çalışmaz; bu beklenen bir gizlilik sınırıdır.

**Model/imaç hazırlığı çevrimiçi yapılır; ardından uygulama izole edilir:**

1. Gerekli Docker imajını önceden indir ve MKAOS imajını oluştur: `docker compose -f docker-compose.yml build sentinel`.
2. Ollama modelleri için hazırlık servisini başlat: `docker compose -f docker-compose.bootstrap.yml up -d`.
3. Modelleri indir:

```bash
docker compose -f docker-compose.bootstrap.yml exec ollama-bootstrap ollama pull qwen2.5:7b
docker compose -f docker-compose.bootstrap.yml exec ollama-bootstrap ollama pull qwen2.5-coder:7b
docker compose -f docker-compose.bootstrap.yml exec ollama-bootstrap ollama pull nomic-embed-text
```
4. Model indirme bittikten sonra hazırlık servisini durdur: `docker compose -f docker-compose.bootstrap.yml down`. **`-v` kullanma**; bu yerel model hacmini silebilir.
5. Yerel Piper ve faster-whisper modellerini `models/voices/` ve `models/whisper-small/` içine yerleştir. Model dosyalarını kaynak depoya ekleme. Ses stüdyosunda erkek tok/bilge ve kadın enerjik/net profilleri ile 0,85×–1,15× hız ayarı bulunur. Kalite gerçek ses modeli, donanım ve dinleme testiyle doğrulanmalıdır; hız/efekt ayarı tek başına “ultra” kalite garantisi değildir.
6. Çevrimdışı çalışma ağını başlat: `docker compose -f docker-compose.yml -f docker-compose.offline.yml up -d --no-build`.

`internal: true` ağı, uygulama konteynerlerinin normal internet çıkışını engeller; ana bilgisayarın veya başka uygulamaların ağ erişimini kendiliğinden sınırlandırmaz. En yüksek güvence için ana bilgisayarın güvenlik duvarı kurallarını da denetle. Çevrimdışı mod, internete bağlanma kabiliyetini azaltır; ama tek başına ana bilgisayardaki her sürecin veri göndermesini engellemez.

## Docker ilk açılış ve RAG sınırları

`docker compose up --build -d` web panelini ve yerel Ollama hizmetini başlatır. `OWNER_PASSWORD` ayarlamadıysan ilk çalıştırmada rastgele parola `/app/memory/first-run-password.txt` içine yerel olarak yazılır; görmek için `docker compose exec sentinel cat /app/memory/first-run-password.txt` çalıştır. Parola uygulama günlüğüne yazılmaz. Panel sağlık denetimi Ollama modelinin hazır olmasına bağlı değildir; `/health` web sürecini, `Durum` paneli ise yerel Ollama bağlantısını ayrıca raporlar. Varsayılan `seka_isolated` ağı çalışma sırasında internet çıkışını engeller; bu yüzden model dosyaları önceden hazırlanmalıdır. Model ilk kurulumda otomatik indirilmez.

İlk kurulumda model hazırlama komutlarını yukarıdaki **Kesin çevrimdışı çalışma profili** bölümünden uygula; ardından `docker compose up --build -d` ile paneli ve Ollama'yı başlat.

`down` komutuna `-v` ekleme; model hacmini silebilir. Bu hazırlık aşamasında model istekleri dış ağa çıkar. Hazırlık tamamlandıktan sonra varsayılan çalışma ağı izoledir. İnternet gerektiren GitHub/web/finans özelliklerini özellikle kullanmak istiyorsan `docker compose -f docker-compose.yml -f docker-compose.networked.yml up --build -d` kullan; bunun yanında ilgili `ALLOW_*` değişkenini de açıkça `true` yapman gerekir. Ağ profilini açmak tek başına entegrasyon izni vermez.

RAG varsayılan olarak en fazla 10.000 parça tutar; bir yüklemede 500 parça ve 1.000.000 karakter sınırı vardır. Tekrarlanan aynı kaynak/parçalar kararlı kimliklerle yinelenmez; sınır aşılırsa en eski parçalar temizlenir. Limitler `SEKA_RAG_MAX_DOCUMENTS`, `SEKA_RAG_MAX_CHUNKS_PER_INGEST` ve `SEKA_RAG_MAX_CHARS_PER_INGEST` ile düşürülebilir; güvenlik tavanları sırasıyla 100.000 parça, 10.000 parça/yükleme ve 10.000.000 karakterdir. Koleksiyon budaması embedding vektörlerini belleğe çekmeden yalnızca kimlik/metadata kullanır. Durum API’si yaklaşık disk kullanımını ve parça sayısını gösterir.

## Otomatik gece denetimi

MKAOS her gece varsayılan olarak 03:00 (Europe/Istanbul) saatinde yerel bakım döngüsü çalıştırır. Döngü güvenlik taraması yapar, yerel model erişilebiliyorsa iyileştirme önerileri üretir ve sonucu `memory/night_reports/` ile `memory/night_scheduler.json` içinde saklar. Zamanlama ve son çalışma `/api/status` üzerinden görüntülenir. `SEKA_NIGHT_AUTORUN=false` ile kapatılabilir; saat ve saat dilimi `SEKA_NIGHT_HOUR`, `SEKA_NIGHT_MINUTE` ve `SEKA_TIMEZONE` ile ayarlanır.

**Güvenlik sınırı:** Gece döngüsü kodu kendiliğinden değiştirmez, komut çalıştırıp push yapmaz ve onayları atlamaz; rapor ve öneri hazırlar. Web/finans/site taraması ilgili `ALLOW_*` iznine bağlıdır ve varsayılan kapalıdır. Bilgisayar tamamen kapalıyken görev çalışmaz; MKAOS'un çalıştığı makine açık ve Docker çalışır durumda olmalıdır.

## Yerel Türkçe ses

- **Erkek sesi:** tok ve bilge profil; varsayılan Piper `tr_TR-fettah-medium`.
- **Kadın sesi:** enerjik ve net profil; varsayılan Piper `tr_TR-dfki-medium`.
- **Kedi dublajı:** yerel `ffmpeg` ile ses perdesi efekti. Modelin gerçek ses rengi, kurulu Türkçe ses paketinin kalitesine bağlıdır; yayımdan önce gerçek cihazda dinleyerek doğrula.
- **Sesli komut:** tarayıcıdaki bulut tabanlı `SpeechRecognition` kullanılmaz. Mikrofon kaydı yalnızca yerel MKAOS sunucusuna gönderilir; çözümleme yerel faster-whisper veya whisper.cpp modeliyle yapılır. Modeller hazır değilse ses işlevi açıkça hata verir.
- Kurulum için `pip install -r requirements-voice.txt` kullanabilir veya Docker imajında isteğe bağlı ses bağımlılıklarını kurabilirsin. Model dosyaları kaynak depoya eklenmemelidir.

## Güvenli kurulum

1. Python 3.12 ve Ollama kur.
2. Yerel modeli ve embedding modelini indir:

```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

3. Repoyu indir ve sanal ortam kur:

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

4. `.env` dosyasında **uzun, benzersiz bir `OWNER_PASSWORD`** belirle. GitHub/WhatsApp anahtarlarını yerel-only kullanım için boş bırak. `.env` dosyasını Git'e ekleme. Docker için `OLLAMA_BASE_URL=http://ollama:11434` kullan; ana makinede Python ile çalıştırırken `OLLAMA_BASE_URL=http://localhost:11434` ayarla.
5. Başlat:

```bash
python -m scripts.run web --host 127.0.0.1 --port 8000
```

Sonra `http://127.0.0.1:8000` adresini aç. Kimlik doğrulama varsayılan olarak açıktır. Docker kullanırken de `OWNER_PASSWORD` değerini belirle; port varsayılan olarak yalnızca loopback arayüzüne bağlanır.

## Komutlar

```bash
python -m scripts.run web --host 127.0.0.1
python -m scripts.run review path/to/file.py
python -m scripts.run secrets --path .
python -m scripts.run licenses --path .
python -m scripts.run permissions
python -m unittest discover -s tests -v
node --check web/static/app.js
```

## Kalıcı veri ve yedek

- Uygulamayı durdurduktan sonra `memory/` dizinini ve yerel `.env` dosyasını ayrı, şifreli bir yedekleme politikasına göre yedekle. `.env` yedeğini kaynak kod deposuna yükleme.
- Yedek geri yüklemeyi periyodik olarak test et. Yedek oluşturmak tek başına geri yüklemenin başarılı olduğunu kanıtlamaz.
- Şifre/erişim bilgilerini değiştirirken eski yedeğin güvenli saklandığından emin ol.

## Geliştirme ilkeleri

1. Yerel model, yerel bellek, açık entegrasyonlar.
2. Varsayılan reddetme ve en az ayrıcalık.
3. Kararlı kimlikli onaylar; push ve harici yan etkiler için insan kontrolü.
4. Güvenli hata mesajları, sınırlandırılmış dosya yükleme, SSRF savunması.
5. Test, bağımlılık ve güvenlik taramalarıyla doğrulama.
6. Bilgi “öğrenimi” otomatik model ağırlıklarını değiştirmez; araştırma girdileri doğrulanır, kaynakları izlenir ve yalnızca açıkça etkinleştirilmişse internet kullanılır.

## Bilinçli sınırlar

Otonom şirket, gerçek para ile alım-satım, izinsiz uzaktan kod çalıştırma, açık P2P ajan sürüsü ve izinsiz IoT kontrolü kapsam dışıdır. Finans modülü sanal/paper modunda kalmalıdır.

## Lisans
MIT


## Test edilen davranış ve doğrulama sınırı

CI; Python derlemesi, JavaScript sözdizimi, Compose profillerinin yapılandırması, Docker imaj derlemesi, güvenlik regresyon testleri ve depodaki muhtemel sabit sırların taramasını çalıştırır. CI’da imaj derlemesi, gerçek cihazda mikrofon/ses kalitesi veya Ollama modeliyle uçtan uca konuşma testinin yerine geçmez. İki Türkçe Piper sesi için yerel model dosyaları kullanıcı tarafından kurulmalıdır; erkek/kadın ses karakteri ve kedi efekti gerçek hoparlör/mikrofon üzerinde ayrıca dinlenip değerlendirilmelidir. 


Ağ gizliliği, çalışma zamanı çıkış testi ve işletim sistemi güvenlik duvarı sınırları için [Ağ Gizliliği Rehberi](docs/NETWORK_PRIVACY.md) belgesine bak.


## Deneysel MKAOS yerel motoru (isteğe bağlı)

MKAOS'un yerleşik HTTP sunucusu model ağırlıklarını ve tokenizer'ı başlangıçta bir kez yükler; aynı sistem istemi tekrar kullanıldığında sınırlı bir KV önek önbelleğinden yararlanır, her isteğin kullanıcı bağlamı için ayrı KV durumu oluşturur. Sunucu güvenlik için yalnızca loopback adresine bağlanır:

```bash
python tools/fetch_model.py
cargo run --release --manifest-path engine/mkaos-hf-adapter/Cargo.toml --bin mkaos_server -- models/smollm2-135m-instruct
```

Varsayılan adres `http://127.0.0.1:11435` şeklindedir. `/health`, `/api/chat`, `/api/generate` ve `/api/tags` uç noktaları desteklenir. İstek gövdesinde `stream: true` kullanıldığında yanıt token parçaları halinde NDJSON akışıyla gönderilir. Sunucu varsayılan olarak aynı anda 4 isteği işler; `MKAOS_MAX_CONCURRENT_REQUESTS` 1–64 aralığında ayarlanabilir. Kapasite dolduğunda sınırsız bellek kuyruğu yerine `503 Service Unavailable` döner.

Uygulamayı MKAOS'a yönlendirmek için `.env` içinde `MKAOS_BASE_URL=http://127.0.0.1:11435` ayarlanır; `MKAOS_ENABLED` sohbet için artık geçersizdir. **Geri alma yok:** sohbet üretimi yalnızca MKAOS'a gider. MKAOS kapalıysa hata görünür; Ollama sohbet sağlayıcısı olarak kullanılmaz. RAG embedding varsayılanı çevrimdışı `mkaos-native` sözcük/karakter n-gram taban çizgisidir; bu eğitilmiş anlamsal bir model değildir. İsteğe bağlı Ollama embedding için `SEKA_EMBEDDINGS_PROVIDER=ollama` ve Compose'ta `--profile legacy-ollama-embeddings` etkinleştirilir; farklı vektör uzayları ayrı koleksiyonlarda tutulur. MKAOS sunucusu çalışmıyorsa uygulama otomatik olarak Ollama'ya geçmez; sessiz sağlayıcı değişimi yerine açık hata davranışı korunur.

Bu özellik deneysel durumdadır. Mevcut aday ağırlıklar üçüncü taraf SmolLM2'dir; bu sunucu kendi ağırlıklarımızı eğitmez. Türkçe kalite, semantik doğruluk ve hedef cihaz performansı sabit değerlendirme kümesiyle ölçülmeden varsayılan yapılmamalıdır. Kalite raporu:

```bash
python tools/evaluate_mkaos_quality.py --model-dir models/smollm2-135m-instruct\n# Sunucu çalışırken tekrar yükleme maliyeti olmadan ölçüm:\npython tools/evaluate_mkaos_quality.py --server-url http://127.0.0.1:11435 --output artifacts/mkaos-resident-quality.json
```


## Türkçe eğitim verisi ve bağımsız kalite kapısı

Eğitim verisi menşei ve izin politikası için [Türkçe veri yönetişimi](docs/MKAOS_TURKISH_DATA_GOVERNANCE.md), bağımsız değerlendirme süreci için [Türkçe değerlendirme protokolü](docs/MKAOS_TURKISH_EVALUATION_PROTOCOL.md) belgelerine bak. Mevcut kalite kümesi yalnızca küçük bir regresyon testidir; MKAOS tarafından eğitilmiş ağırlık veya Türkçe yeterlilik sertifikası değildir. Gerçek eğitim, izinleri gözden geçirilmiş veri kümesi, ayrılmış test bölümü, hesaplama kaynağı ve bağımsız değerlendirme gerektirir.


## MKAOS ağırlıklarını sıfırdan eğitme (deneysel)

`tools/train_mkaos_from_scratch.py`, başka bir modelin ağırlıklarını indirmeden rastgele başlatılmış MKAOS GQA/SwiGLU decoder'ını eğitir ve Rust motorunun `MKAOSW1` checkpoint biçimine aktarır. Bu yol, önceden eğitilmiş bir LLM'yi yeniden adlandırmaz veya onun ağırlıklarını kullanmaz. Eğitim için ayrıca yerel, insan/hukuk incelemesinden geçmiş Türkçe veri gerekir; repoda hazır/onaylı bir eğitim korpusu bulunması anlamına gelmez.

- JSONL satırları: `{"sample_id":"...","text":"..."}`; her metnin SHA-256 değeri manifestteki örnekle eşleşmelidir.
- Manifest kapısı: `tools/validate_mkaos_training_manifest.py` içindeki tüm kaynak/lisans/izin/PII/split kontrolleri geçmelidir.
- Eğitim komutu: `python tools/train_mkaos_from_scratch.py --corpus ./approved-tr.jsonl --manifest ./approved-manifest.json --output-dir ./artifacts/mkaos-tr`
- Eğitim gereksinimi: yerel kurulumda PyTorch; hiçbir model deposuna veya indirme API'sine başvurulmaz.
- Çıktılar: `mkaos-owned.mkaosw`, `tokenizer.json` ve hash/seed/cihaz/kayıp bilgilerini içeren `training-report.json`.
- Yerel Rust CLI ile üretim: `cargo run --release --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-generate -- --checkpoint ./artifacts/mkaos-tr/mkaos-owned.mkaosw --sha256 <checkpoint_sha256> --heads 4 --kv-heads 2 --max-seq 128 --max-new-tokens 32 --prompt "Merhaba"` (baş/katman boyutlarını eğitim raporundan kullanın).
- Test bölümü optimizasyon ve model seçimi için kullanılmaz. Çalıştırma raporu Türkçe yetenek sertifikası değildir; bağımsız held-out değerlendirme ve Rust motorunda checkpoint yükleme/yanıt testi hâlâ gerekir.

Bu küçük byte-tokenizer modeli başlangıç araştırma hattıdır; üretim kalitesinde Türkçe asistan, GPU hızlandırması, dağıtık durum veya canlı mesh tamamlanmış sayılmaz.

## Open source worldwide

MKAOS is developed in public under the repository's MIT license. No institutional endorsement or certification is claimed. MIT applies to this repository's covered source; third-party model weights, datasets, voices, and assets may have separate terms. Public availability alone does not grant training or redistribution permission.

Read the current evidence and contribution policy in [MKAOS Open-Source Readiness](docs/MKAOS_OPEN_SOURCE_READINESS.md). The current source register contains **zero approved training sources**, so a real owned-model training run is not yet cleared to start. Host-metadata CI and ARM64 tests do not certify native inference on every platform. We will publish stronger claims only alongside reproducible evidence.


## MKAOS yerel sembolik akıl yürütme başlangıcı

Önceden eğitilmiş ağırlık veya ağ çağrısı olmadan çalışan küçük Rust başlangıç çekirdeği `engine/mkaos-inference/LOCAL_REASONING.md` içinde belgelenmiştir. `mkaos-reason` komutu temel aritmetik ve açık `A ise B. A` kuralından tek adımlı çıkarım yapar; genel amaçlı LLM değildir. Test etmek için `cargo test --manifest-path engine/mkaos-inference/Cargo.toml` komutunu çalıştır. Bu yeni çekirdek uygulama sohbet API'sinin model tabanlı yolunu değiştirmez.


## Hugging Face portability and offline hardening

The dependency-free, read-only local checkpoint inspector is `tools/mkaos_hf_adapter_preflight.py`; guide: [HF portability, output guardrails, PEFT and offline operation](docs/MKAOS_HF_PORTABILITY_AND_OFFLINE_SECURITY.md). It does not convert arbitrary `.safetensors` weights into `MKAOSW1`: architecture, tokenizer and numerical parity must be implemented and tested first. Final reasoning output now passes through a narrow local guard that redacts high-confidence credential-shaped strings; this is not a general fact-checker or model-safety certification. Dataset/model license, privacy, attribution and training approval gates remain mandatory.

The Hugging Face architecture decision table and required parity protocol are in [MKAOS HF compatibility matrix](docs/MKAOS_HF_COMPATIBILITY_MATRIX.md). A pinned SmolLM2-135M-Instruct CPU reference smoke workflow is defined at `.github/workflows/mkaos-hf-cpu-smoke.yml`. Its repeat-logit check validates the reference runtime only; it does not claim MKAOSW1 conversion parity. Numerical comparison metrics are implemented in `tools/mkaos_numerical_parity.py`.


---

# English

## MKAOS — Sentinel Agent Intelligence

MKAOS is a Turkey-based, open-source project exploring a local-first, human-supervised agent platform. **It is not accurately described as “100% domestic” or fully sovereign today.** The repository uses third-party open-source software, and model weights, datasets, hardware, build tools, and supply-chain components can have separate origins and licenses.

### Current status — October 2026

- **Native language model:** No approved, production-ready MKAOS-trained checkpoint or independently validated Turkish quality score is currently provided. The default native chat path fails closed with HTTP 503 when the required checkpoint is absent. A synthetic CI smoke test is not evidence of useful Turkish language quality.
- **Local-first operation:** Network-dependent integrations are configurable and should remain disabled for offline use. Application settings alone are not a guarantee that every host process is offline; apply and verify host firewall/network policy too.
- **MCP:** A minimal read-only stdio MCP server is provided. It exposes a bounded workspace text-reading tool, not arbitrary shell execution or unrestricted file access.
- **Crypto-RAG:** An opt-in AES-GCM encrypted SQLite vector-store backend and migration/verification tooling are available. The migration is not automatically run against user data and does not delete the source store. Existing Chroma or plaintext data is not automatically encrypted by enabling this backend.
- **Browser worker:** A restricted Playwright screenshot lab targets an allowlisted local fixture. It is not a general-purpose live scanning service; live targets and interactions require explicit authorization and further operational controls.
- **Agent mesh:** mTLS policy helpers and WireGuard deployment guidance are included, but live WireGuard interfaces, peer keys, firewall rules, certificate distribution, and revocation infrastructure are not provisioned by this repository change.
- **Post-quantum cryptography (PQC):** ML-KEM, ML-DSA, or hybrid post-quantum transport is **not enabled in production**. Enablement requires pinned implementations, licensing and supply-chain review, interoperability tests, and tested key/certificate lifecycle management. WireGuard alone is not a post-quantum or application-level end-to-end encryption solution.
- **UI and identity:** The dashboard uses a geometric silver/violet MKAOS emblem and a dark obsidian/violet palette. The emblem is the compact interface mark; the Atatürk-themed concept artwork is better suited to a presentation or cover image.

### Quick start

Prerequisites: Python 3.12; Docker Compose is recommended. A real native chat model and local embedding model must be provisioned separately; model weights are not bundled in this repository.

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Set a long, unique `OWNER_PASSWORD` in `.env`, keep secrets out of Git, and review the local model and RAG setup instructions above before starting. For a local-only development server:

```bash
python -m scripts.run web --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. For the Docker path, follow the repository's offline profile and model preparation instructions; do not assume the models are downloaded or that the native chat endpoint will work without a valid checkpoint.

### Tests and checks

```bash
python -m unittest discover -s tests -v
node --check web/static/app.js
python -m scripts.run secrets --path .
python -m scripts.run licenses --path .
```

CI success applies only to the specific commit and jobs shown in GitHub Actions. A skipped model-training job is not a successful training run. Report TTFT, tokens/second, memory, and Turkish quality only with the model/checkpoint, hardware, test set, and measurement procedure identified.

### Security and data migration

1. Back up the existing store and verify that the backup can be restored.
2. Run migration only against a quiesced source and a separate destination.
3. Compare record counts, metadata, document contents, embeddings, and integrity hashes before switching readers.
4. Keep the original plaintext store until a verified backup and explicit owner approval exist. This repository change does not delete it.
5. Never put API keys, private keys, model weights, personal datasets, or runtime secrets in Git.

### Roadmap and limitations

MKAOS aims to provide auditable local inference, Turkish-language tooling, encrypted retrieval, controlled MCP tools, an isolated browser worker, and authenticated agent communication. Some parts are foundations or opt-in helpers, not fully deployed production services. The project does not claim full model independence, universal hardware acceleration, production PQC, a live zero-trust mesh, or certified Turkish model quality without reproducible evidence.

See [MKAOS Open-Source Readiness](docs/MKAOS_OPEN_SOURCE_READINESS.md), [independence milestones](docs/MKAOS_INDEPENDENCE_MILESTONES.md), [Turkish data governance](docs/MKAOS_TURKISH_DATA_GOVERNANCE.md), and [network privacy guide](docs/NETWORK_PRIVACY.md).

### Contributing

Issues, reproducible bug reports, tests, and carefully scoped pull requests are welcome. Please include reproduction steps, environment details, expected versus actual behavior, and test evidence. Do not include secrets or private user data. Security-sensitive issues should be reported privately where repository settings permit.

### License

The repository declares MIT licensing. Third-party code, model weights, datasets, voices, and artwork may have their own license or usage conditions; check each source separately. Public availability does not automatically grant permission to train on or redistribute a dataset or model.

---

## Dil / Language

- **Türkçe:** [Yukarıdaki Türkçe bölümler](#mkaos-v65--mustafa-kemal-atatürk-operating-system)
- **English:** [English documentation](#english)

