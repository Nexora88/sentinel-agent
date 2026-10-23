# MKAOS tek tuş kurulum ve cihaz profilleri

## Windows

1. Repoyu ZIP olarak indirin ve klasöre çıkarın.
2. İnternet bağlantısı açıkken `INSTALL_MKAOS_WINDOWS.bat` dosyasını çalıştırın.
3. Python 3.12 kurulu olmalıdır. Kurulum bağımlılıkları sanal ortama yükler, `.env` oluşturur, rastgele bir yerel yönetici parolası üretir ve sunucuyu yalnızca `127.0.0.1` üzerinde başlatır.
4. Profil sorusunda 8 GB veya 16 GB seçin. Bu seçim RAM eklemez ve gerçek RAM miktarını değiştirmez; yalnızca tercih kaydıdır. Otomatik profil ayarlaması yapılmış gibi düşünmeyin.
5. Arayüz `http://127.0.0.1:8000` adresinde açılır. Parola `.env` içindeki `OWNER_PASSWORD` değeridir; bu dosyayı kimseyle paylaşmayın.

## Sistem gereksinimleri

- Windows 10/11 x64 ve Python 3.12.
- Kurulum sırasında Python paketlerini indirmek için internet bağlantısı.
- Kurulum sonrası arayüzün kendisi yerel olarak çalışabilir; ancak gerçek çevrimdışı sohbet için uyumlu model ağırlıkları, tokenizer ve yerel çıkarım motoru önceden kurulmuş olmalıdır.
- 8 GB RAM temel kullanım profili; 16 GB profil daha fazla bellek payı sağlar. Gerçek modelin RAM gereksinimi model boyutuna, bağlam uzunluğuna ve çalışma biçimine bağlıdır. 3–4 GB RAM'li cihazlarda LLM sohbeti yavaş olabilir veya çalışmayabilir.
- Disk alanı model dosyalarına göre değişir. Model ağırlıkları kurulum paketine dahil değildir.

## Çevrimdışı çalışma ve gizlilik

- Kurulumun kendisi paketleri indirdiği için internet gerektirir. Sonrasında uygulamayı açmak internet gerektirmeyebilir; harici entegrasyonlar ve indirilmemiş model dosyaları çalışmaz.
- Yerel sunucu varsayılan olarak `127.0.0.1` adresine bağlanır; yerel ağdaki diğer cihazlara açılmaz.
- Gerçek çevrimdışı garantisi için işletim sistemi güvenlik duvarında ağ çıkışını ayrıca engelleyip modeli internet kapalıyken başlatma ve yanıt alma testi yapılmalıdır.
- Model ağırlıkları, veri kümeleri ve ses paketleri ayrı lisanslara tabi olabilir. Kullanım/yeniden dağıtım izinleri doğrulanmadan indirme veya eğitim otomatikleştirilmez.

## Sınırlamalar

Bu betik kurulum akışını sadeleştirir; model ağırlıklarını üretmez veya otomatik olarak eğitmez. Model yoksa kurulumun başarılı olması sohbetin hazır olduğu anlamına gelmez. Gerçek TTFT, token/saniye, RAM ve Türkçe kalite ölçümleri uyumlu model ve akış zaman damgalarıyla ayrıca alınmalıdır.
