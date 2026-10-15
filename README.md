# SEKA v6.1 — Sentinel Agent

**Yerel Türkçe ajan altyapısı.** Ollama üzerinden yerel çıkarım; bulut model API'si zorunlu değildir. Güvenlik, veri sahipliği ve insan onayı temel ilkedir.

SEKA; görev planlama, yerel bilgi deposu, kod inceleme, savunmacı güvenlik taraması, iş kuyruğu ve isteğe bağlı GitHub araçlarını bir araya getirir. “Kendi kararlarını vermek”, hedefler için plan önermek ve güvenli yerel işleri yürütmek anlamına gelir. Dosya değiştirme, commit, push, bildirim veya harici sisteme veri gönderme gibi etkiler açık onay gerektirir.

## Gizlilik modeli ve sınırlar

- **Yerel çıkarım:** Ollama istemcisi yalnızca loopback veya yerel Docker uç noktasını kabul eder; uzak model/API uç noktaları reddedilir. Varsayılan model \`qwen2.5-coder:7b\`; embedding modeli \`nomic-embed-text\`.
- **Yerel saklama:** kullanıcıya göre ayrılmış sohbet geçmişi ve onay günlüğü atomik dosya yazımıyla yerel `memory/` içinde tutulur; bozuk veri sessizce sıfırlanmaz. Bellek ve vektör deposu da yerel proje/volume içindedir. Bu dizini şifreli disk üzerinde tut ve yedekle.
- **Web araştırması kapalı başlar:** `ALLOW_WEB_RESEARCH=false` iken bilgi genişletme arama sorgusu göndermez. Bilerek açarsan arama sorguları ve sayfa istekleri internete çıkar. GitHub token'ı GitHub'a istek gönderir. Üçüncü taraf bildirimleri `ALLOW_EXTERNAL_NOTIFICATIONS=true` ile açıkça etkinleştirilmedikçe kapalıdır. Tam çevrimdışı kullanım için bu özellikleri çalıştırma, kimlik bilgilerini tanımlama ve ağ çıkışını işletim sistemi/firewall seviyesinde kısıtla.
- **Onay varsayılanı açık:** GitHub yazma, commit, push ve dosya değişiklikleri otomatik yapılmamalıdır. Her onay kararlı bir istek kimliğine bağlıdır.
- **Savunmacı tarama:** web tarayıcısı yerel/özel IP'leri ve doğrulanmayan yönlendirmeleri engeller. Yalnızca sahibi olduğun veya tarama iznin olan hedeflerde kullan.
- **Güvenlik dürüstlüğü:** uygulama tek başına “veri asla dışarı çıkamaz” garantisi veremez. Bu; uygulama ayarlarına, işletim sistemi/firewall'a, model endpoint'ine, yedeklemeye ve etkinleştirilen entegrasyonlara bağlıdır.

## Kesin çevrimdışı çalışma profili

`docker-compose.offline.yml` ayrı bir çalışma zamanı profili sağlar: SEKA ve Ollama yalnızca birbirleriyle konuşan, internet çıkışı olmayan bir Docker ağına bağlanır. GitHub token'ı, web araştırması, dış bildirim ve harici görsel üretimi bu profilde kapalıdır. Bu nedenle canlı finans verisi, GitHub yazma ve web taraması çevrimdışı profilde çalışmaması beklenen özelliklerdir.

1. Docker imajlarını ve gerekli Ollama modellerini internet bağlantısı varken önceden hazırla.
2. `models/voices/` içine Piper'ın Türkçe `tr_TR-fettah-medium.onnx` ve `tr_TR-dfki-medium.onnx` dosyalarını (ve eşlik eden `.onnx.json` dosyalarını) yerleştir.
3. `models/whisper-small/` içine yerel faster-whisper uyumlu model dosyalarını yerleştir. Model bulunamazsa konuşma özelliği hata verir; otomatik bulut yedeği yoktur.
4. İlk hazırlık ve model indirmeleri bittikten sonra `docker compose -f docker-compose.yml -f docker-compose.offline.yml up -d --build` komutuyla çalıştır. Model/imaj hazırlığını tamamladıktan sonra ağı internetten yalıtılmış halde tut.

`internal: true` ağı, uygulama konteynerlerinin normal internet çıkışını engeller; yine de bu, ana bilgisayarın veya başka uygulamaların ağ erişimini sınırlandırmaz. En yüksek güvence için ana bilgisayarın güvenlik duvarı kurallarını da denetle.

## Yerel Türkçe ses

- **Erkek sesi:** tok ve bilge profil; varsayılan Piper `tr_TR-fettah-medium`.
- **Kadın sesi:** enerjik ve net profil; varsayılan Piper `tr_TR-dfki-medium`.
- **Kedi dublajı:** yerel `ffmpeg` ile ses perdesi efekti. Modelin gerçek ses rengi, kurulu Türkçe ses paketinin kalitesine bağlıdır; yayımdan önce gerçek cihazda dinleyerek doğrula.
- **Sesli komut:** tarayıcıdaki bulut tabanlı `SpeechRecognition` kullanılmaz. Mikrofon kaydı yalnızca yerel SEKA sunucusuna gönderilir; çözümleme yerel faster-whisper veya whisper.cpp modeliyle yapılır. Modeller hazır değilse ses işlevi açıkça hata verir.
- Kurulum için `pip install -r requirements-voice.txt` kullanabilir veya Docker imajında isteğe bağlı ses bağımlılıklarını kurabilirsin. Model dosyaları kaynak depoya eklenmemelidir.

## Güvenli kurulum

1. Python 3.12 ve Ollama kur.
2. Yerel modeli ve embedding modelini indir:

\`\`\`bash
ollama serve
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
\`\`\`

3. Repoyu indir ve sanal ortam kur:

\`\`\`bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
\`\`\`

4. \`.env\` dosyasında **uzun, benzersiz bir \`OWNER_PASSWORD\`** belirle. GitHub/WhatsApp anahtarlarını yerel-only kullanım için boş bırak. \`.env\` dosyasını Git'e ekleme.
5. Başlat:

\`\`\`bash
python -m scripts.run web --host 127.0.0.1 --port 8000
\`\`\`

Sonra \`http://127.0.0.1:8000\` adresini aç. Kimlik doğrulama varsayılan olarak açıktır. Docker kullanırken de \`OWNER_PASSWORD\` değerini belirle; port varsayılan olarak yalnızca loopback arayüzüne bağlanır.

## Komutlar

\`\`\`bash
python -m scripts.run web --host 127.0.0.1
python -m scripts.run review path/to/file.py
python -m scripts.run secrets --path .
python -m scripts.run licenses --path .
python -m scripts.run permissions
python -m unittest discover -s tests -v
node --check web/static/app.js
\`\`\`

## Kalıcı veri ve yedek

- Uygulamayı durdurduktan sonra \`memory/\` dizinini ve yerel \`.env\` dosyasını ayrı, şifreli bir yedekleme politikasına göre yedekle. \`.env\` yedeğini kaynak kod deposuna yükleme.
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
