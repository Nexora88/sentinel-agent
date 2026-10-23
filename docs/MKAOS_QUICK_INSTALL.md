# MKAOS tek tuş kurulum ve cihaz profilleri

## Windows — en kısa kurulum

1. [MKAOS kaynak paketini ZIP olarak indir](https://github.com/Nexora88/sentinel-agent/archive/refs/heads/main.zip).
2. ZIP'i bir klasöre çıkar.
3. Çıkarılan `sentinel-agent-main` klasöründeki `INSTALL_MKAOS_WINDOWS.bat` dosyasına çift tıkla.
4. Windows bir onay gösterirse yalnızca dosyayı bu resmî GitHub deposundan indirdiğini doğruladıktan sonra devam et.
5. Kurulum tamamlanınca tarayıcıda `http://127.0.0.1:8000` adresini aç. Oluşturulan yerel yönetici parolası proje klasöründeki `.env` dosyasındaki `OWNER_PASSWORD` değeridir; bunu paylaşma.

Bu, tek indirmeli ve çift tıklamalı **kurulum akışıdır**; imzalı bir Windows `.exe` yükleyicisi değildir. ZIP'i çıkarmak ve Windows güvenlik uyarılarını gözden geçirmek gerekir. Kaynak kodu incelemeden çalıştırma.

## Gereksinimler ve sohbetin gerçek durumu

- Windows 10/11 x64 ve Python 3.12.
- Paketleri kurmak için ilk kurulumda internet bağlantısı.
- Kurulum sanal ortamı ve Python bağımlılıklarını hazırlar, gerekiyorsa `.env` oluşturur ve web sunucusunu yalnızca `127.0.0.1` üzerinde başlatır.
- Model dosyaları kurulum paketine dahil değildir. Uyumlu yerel model sunucusu, checkpoint ve tokenizer hazır değilse arayüz açılsa bile sohbet 503 döndürebilir. Kurulum başarısı, modelin Türkçe doğru yanıt verdiğinin kanıtı değildir.
- Profil seçimleri (8/16 GB) RAM eklemez; yalnızca yapılandırma tercihidir. 3–4 GB RAM'li cihazlarda LLM sohbeti yavaş olabilir veya hiç çalışmayabilir.

## Çevrimdışı çalışma ve gizlilik

- İlk kurulum internet gerektirir. Sonrasında web arayüzü yerel çalışabilir; fakat indirilmemiş model, uzak entegrasyonlar ve güncellemeler çalışmaz.
- Yerel sunucu varsayılan olarak `127.0.0.1` adresine bağlanır; yerel ağdaki diğer cihazlara açılmaz.
- Gerçek çevrimdışı garantisi için işletim sistemi güvenlik duvarında ağ çıkışı ayrıca engellenmeli ve model internet kapalıyken başlatılıp test edilmelidir.
- Model ağırlıkları, veri kümeleri ve ses paketleri ayrı lisanslara tabi olabilir. Kullanım/yeniden dağıtım izinleri doğrulanmadan indirme veya eğitim otomatikleştirilmez.

## Ölçüm ve sınırlamalar

Bu kurulum betiği model üretmez veya eğitmez. Gerçek Türkçe kalite testi geçmeden ve sabit checkpoint/tokenizer/donanım ile tekrarlanabilir TTFT, token/s ve bellek raporu alınmadan sohbet performansı iddiası yayımlanmaz.
