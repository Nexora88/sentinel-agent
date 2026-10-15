# MKAOS v6.5 — Mustafa Kemal Atatürk Operating System

**Yerel Türkçe ajan işletim sistemi altyapısı.** HTTP sohbet yolu artık varsayılan olarak yerel Rust `mkaos-generate` CLI'ına gider ve onaylı yerel checkpoint yoksa açıkça `503` döndürür; üçüncü taraf SmolLM2'ye sessiz geri dönüş yapılmaz. Ancak henüz onaylı Türkçe korpus, eğitilmiş kullanılabilir MKAOS checkpoint'i veya bağımsız Türkçe kalite kanıtı yoktur. Sentetik CI eğitimi mimari/aktarım testidir; gerçek Türkçe yetenek kanıtı değildir. Güvenlik, veri sahipliği ve insan onayı temel ilkedir.

MKAOS; görev planlama, yerel bilgi deposu, kod inceleme, savunmacı güvenlik taraması, iş kuyruğu ve isteğe bağlı GitHub araçlarını bir araya getirir. Sohbet üretimi yalnızca MKAOS servisine gider; `MKAOS_ENABLED` sağlayıcı değiştirmez ve MKAOS erişilemiyorsa hata görünür kalır. RAG varsayılanı çevrimdışı `mkaos-native` sözcük/karakter n-gram taban çizgisidir. Bu eğitilmiş semantik embedding modeli değildir; eski Ollama embedding sağlayıcısı yalnızca açık opt-in ile kullanılabilir.

## Bağımsız çıkarım motoru — aşamalı geçiş

- Çekirdek: [engine/mkaos-inference/](engine/mkaos-inference/) — Rust CPU tensör işlemleri, Transformer decoder ve KV cache.
- Eğitim: tools/train_mkaos_from_scratch.py rastgele başlatılmış ağırlıklarla eğitim altyapısı sağlar; yalnızca onaylı yerel korpus ve manifest kabul edilir.
- HTTP sohbet adaptörü: core/mkaos_native_chat.py yerel mkaos-generate ikilisini shell kullanmadan çalıştırır; hash, boyut, zaman aşımı ve çıktı sınırlarını denetler.
- Docker imajı Rust CLI'ı çok aşamalı derlemeyle paketler. Model ağırlıkları otomatik indirilmez ve depoya dahil edilmez.
- Şimdilik onaylı Türkçe korpus veya eğitilmiş kullanılabilir checkpoint yoktur. Bu nedenle varsayılan sohbet, checkpoint yapılandırılana kadar açık HTTP 503 döndürür; üçüncü taraf modele sessiz geri dönüş yoktur.
- Üçüncü taraf SmolLM2 uyumluluk servisi yalnızca açıkça seçilen legacy-third-party-chat Compose profili ile başlatılabilir.
- RAG varsayılanı çevrimdışı yerel sözcük/karakter n-gram taban çizgisidir; eğitilmiş semantik embedding modeli değildir.

### Başlatma

1. .env.example dosyasını .env olarak kopyala.
2. Onaylı korpusla eğitim ve bağımsız inceleme tamamlandıktan sonra checkpoint'i models/mkaos/model.mkaosw içine yerleştir; eğitim raporundaki SHA-256 değerini MKAOS_NATIVE_SHA256 olarak ayarla. Heads/KV-heads/sequence ayarları checkpoint mimarisiyle eşleşmelidir.
3. docker compose up --build komutuyla başlat. Checkpoint yokken chat'in 503 dönmesi beklenen fail-closed davranışıdır.

Yol haritası: [docs/MKAOS_INDEPENDENCE_MILESTONES.md](docs/MKAOS_INDEPENDENCE_MILESTONES.md).

## Native Rust chat integration status

- `POST /api/chat` defaults to `MKAOS_CHAT_BACKEND=native-rust` and invokes the locally packaged Rust CLI without a shell.
- The checkpoint must be supplied locally at `models/mkaos/model.mkaosw` and its SHA-256 set through `MKAOS_NATIVE_SHA256`; the repository intentionally does not bundle model weights.
- Until an approved corpus produces a real checkpoint, chat returns HTTP 503. It does not silently use third-party weights.
- The third-party SmolLM2 compatibility service is gated behind the explicit `legacy-third-party-chat` Compose profile.
- This wiring is not proof of useful Turkish quality, production performance, full supply-chain independence, or completed hardware/distributed validation.

## Marka ve tasarım ilkesi

MKAOS, *Mustafa Kemal Atatürk Operating System* anlamıyla yerel egemenlik, bilim ve üretim hedefini temsil eder. Arayüz sloganı: **“İstikbal Siber Göklerdedir.”** Marka veya ağ durumu tek başına güvenlik kanıtı değildir; “TAM EGEMEN / AIR-GAPPED” yalnızca ağ çıkışı gerçekten sınırlandırılıp doğrulandığında kullanılmalıdır.

## Gizlilik modeli ve sınırlar

- **Yerel çıkarım:** Ollama istemcisi yalnızca loopback veya yerel Docker uç noktasını kabul eder; uzak model/API uç noktaları reddedilir. Varsayılan sohbet modeli `qwen2.5:7b`; kod/derin analiz modeli `qwen2.5-coder:7b`; embedding modeli `nomic-embed-text`.
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
