# SEKA ağ gizliliği ve çıkış denetimi

## Varsayılan koruma

- Standart `docker-compose.yml`, SEKA ile Ollama'yı `internal: true` Docker ağına bağlar. Bu, çalışma zamanında konteynerlerin normal internet çıkışını engeller.
- SEKA web paneli sadece ana makinenin loopback adresine (`127.0.0.1`) yayımlanır.
- Ollama portu ana makineye yayımlanmaz; SEKA ona yalnızca Docker içindeki `ollama:11434` adıyla erişir.
- Web araştırması, dış finans verisi, site taraması ve dış bildirimler varsayılan olarak kapalıdır.
- `docker-compose.networked.yml` ağı bilinçli olarak dışarı açar. Sıkı gizlilik gereken oturumlarda bu dosyayı kullanma.

## Ağın dışarı açık olduğu hazırlık aşaması

Docker imajı/bağımlılık indirmek ve Ollama modelini ilk kez hazırlamak internet erişimi gerektirir. Bu sırada model deposuna istek gönderilir; henüz SEKA'ya özel sohbet verisi eklenmemelidir. Model hacmi hazırlandıktan sonra hazırlık servisini durdur ve standart izole profili başlat. Model indirmek için otomatik başlangıç indirmesi yapılmaz.

## Çalışma zamanı çıkışını doğrulama

SEKA başlatıldıktan sonra aşağıdaki kontrolün başarısız olması beklenir; yani konteyner içinden genel internet hedefine erişilememelidir:

```bash
docker compose exec sentinel python -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)"
```

Bu komut hata verirse, varsayılan izole ağ için beklenen davranış görülmüştür. Ağ profili açıksa bu test başarısızlıkla sonuçlanmayabilir. Ayrıca `docker network inspect` ile SEKA'nın gerçekten `internal: true` ağına bağlı olduğunu kontrol et.

## İşletim sistemi / güvenlik duvarı sınırı

Bu depo, kullanıcının Windows/macOS/Linux ana bilgisayarındaki güvenlik duvarını kendiliğinden değiştirmez. Bu tür değişiklikler başka uygulamaların bağlantısını kesebileceği için otomatik ve sessiz uygulanmamalıdır.

- **Windows/macOS + Docker Desktop:** konteyner ağı Linux sanal makinesi üzerinden çalışır. Docker Desktop arka ucunu genel olarak engellemek diğer projelerin konteynerlerini de bozabilir. En güçlü ek izolasyon için modelleri önceden hazırladıktan sonra SEKA'yı ayrı bir sanal makinede çalıştır ve o VM'nin dış ağını hipervizör/güvenlik duvarı düzeyinde kapat.
- **Linux:** Docker'ın `internal: true` ağına ek olarak, sistem yöneticisi yalnızca SEKA'nın oluşturduğu Docker köprü ağı için dışarı yönlendirilen trafiği güvenlik duvarında reddedebilir. Kurala başlamadan önce `docker network inspect` ile gerçek ağ adı ve alt ağı belirle; genel `FORWARD` zincirini veya tüm Docker trafiğini körlemesine engelleme.
- Ana bilgisayarın kendisinde çalışan başka süreçler, yedekleme yazılımları veya Docker indirme işlemleri bu konteyner ağı kuralıyla otomatik olarak kısıtlanmaz.

**Dürüst garanti:** varsayılan çalışma profili SEKA konteynerlerinin internet çıkışını sınırlar; tüm ana bilgisayardaki bütün süreçler için mutlak “hiçbir veri çıkamaz” garantisi değildir. Tam izolasyon için ağ hazırlığı bittikten sonra VM/işletim sistemi güvenlik duvarı politikasını da ayrıca doğrulamak gerekir.
