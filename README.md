# SEKA v6 — Sentinel Agent

**Yerel Türkçe ajan altyapısı.** Ollama üzerinden yerel çıkarım; bulut model API'si zorunlu değildir. Güvenlik, veri sahipliği ve insan onayı temel ilkedir.

SEKA; görev planlama, yerel bilgi deposu, kod inceleme, savunmacı güvenlik taraması, iş kuyruğu ve isteğe bağlı GitHub araçlarını bir araya getirir. “Kendi kararlarını vermek”, hedefler için plan önermek ve güvenli yerel işleri yürütmek anlamına gelir. Dosya değiştirme, commit, push, bildirim veya harici sisteme veri gönderme gibi etkiler açık onay gerektirir.

## Gizlilik modeli ve sınırlar

- **Yerel çıkarım:** Ollama istemcisi yalnızca loopback veya yerel Docker uç noktasını kabul eder; uzak model/API uç noktaları reddedilir. Varsayılan model \`qwen2.5-coder:7b\`; embedding modeli \`nomic-embed-text\`.
- **Yerel saklama:** kullanıcıya göre ayrılmış sohbet geçmişi ve onay günlüğü atomik dosya yazımıyla yerel `memory/` içinde tutulur; bozuk veri sessizce sıfırlanmaz. Bellek ve vektör deposu da yerel proje/volume içindedir. Bu dizini şifreli disk üzerinde tut ve yedekle.
- **Web araştırması kapalı başlar:** `ALLOW_WEB_RESEARCH=false` iken bilgi genişletme arama sorgusu göndermez. Bilerek açarsan arama sorguları ve sayfa istekleri internete çıkar. GitHub token'ı GitHub'a istek gönderir. Üçüncü taraf bildirimleri `ALLOW_EXTERNAL_NOTIFICATIONS=true` ile açıkça etkinleştirilmedikçe kapalıdır. Tam çevrimdışı kullanım için bu özellikleri çalıştırma, kimlik bilgilerini tanımlama ve ağ çıkışını işletim sistemi/firewall seviyesinde kısıtla.
- **Onay varsayılanı açık:** GitHub yazma, commit, push ve dosya değişiklikleri otomatik yapılmamalıdır. Her onay kararlı bir istek kimliğine bağlıdır.
- **Savunmacı tarama:** web tarayıcısı yerel/özel IP'leri ve doğrulanmayan yönlendirmeleri engeller. Yalnızca sahibi olduğun veya tarama iznin olan hedeflerde kullan.
- **Güvenlik dürüstlüğü:** uygulama tek başına “veri asla dışarı çıkamaz” garantisi veremez. Bu; uygulama ayarlarına, işletim sistemi/firewall'a, model endpoint'ine, yedeklemeye ve etkinleştirilen entegrasyonlara bağlıdır.

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
