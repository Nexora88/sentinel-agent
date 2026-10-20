# MKAOS Ajan Ürünü, Gizlilik ve Güvenlik Yol Haritası

Bu belge ürün tasarımını ve henüz uygulanmamış işleri birbirinden ayırır. Bir özelliğin burada yazması, mevcut sürümde çalıştığı anlamına gelmez.

## Ürün hedefi: sohbet botu değil, denetlenebilir ajan

Ajanın ana döngüsü: **isteği anla → izinleri ve kapsamı kontrol et → planı göster → işi küçük adımlarla yürüt → ilerlemeyi bildir → test et → sonucu kanıtla → öğrenme kaydını güncelle**. Model yalnızca planlama/öneri yapar; dosya, terminal, GitHub ve ağ erişimi ayrı, dar kapsamlı araç izinlerinden geçer.

- İzinli proje listesi ve çalışma dizini sınırları zorunludur. Her yeni depo/klasör ayrıca kullanıcı tarafından yetkilendirilmelidir.
- Yerel bilgisayar köprüsü ayrı, kullanıcının başlattığı bir servis olmalıdır. Sadece seçilmiş proje dizinlerine erişir; gizli dosyaları, tarayıcı profillerini, parolaları ve SSH anahtarlarını varsayılan olarak dışarıda bırakır.
- Dosya düzenleme, komut çalıştırma, bağımlılık ekleme, ağ erişimi ve GitHub yazma ayrı izinlerdir. Silme, sistem yönetici yetkisi, yayınlama ve `main` birleştirme her zaman açık insan onayı gerektirir.
- Çalışma alanı izole worktree/container içinde olmalı; ağ çıkışı varsayılan kapalı olmalı; CPU/RAM/disk ve zaman sınırları uygulanmalıdır.
- Durum mesajları gerçek olaylardan üretilmelidir: “`index.html` okunuyor”, “JavaScript sözdizimi kontrolü başladı”, “`ReferenceError` bulundu”, “düzeltme uygulandı”, “regresyon testi geçti/kaldı”. İşlem gerçekleşmeden başarı cümlesi gösterilmez. Sırlar, tam komut satırları ve özel kod mesajlarda maskelenir.

## Öğrenme döngüsü

Night Watch artık başarısız denetimlerin hassas olmayan parmak izlerini, tekrar sayısını ve regresyon testi gereksinimini sınırlı bir JSON hafızasında tutacak; hafıza GitHub Actions cache'iyle geceler arasında taşınır. Her gece aynı izinli denetimler tekrar çalıştırılır ve eski kayıtların yeniden kontrol sonucu raporlanır.

- Ham terminal çıktısı, kaynak kodu, token, ses kaydı veya kullanıcı sohbeti öğrenme hafızasına yazılmaz.
- Kayıt bir hatayı tekrar üretmek için test eklenmesi gerektiğini belirtir. Test yazma ve kod düzeltme adımı henüz otomatik değildir; sonraki aşamada ayrı worktree'de taslak üretilmeli, test edilmeli ve PR olarak sunulmalıdır.
- Başarısız düzeltme otomatik olarak “öğrenildi/çözüldü” sayılmaz. Başarı, ilgili denetim yeniden çalıştırılıp geçtiğinde kaydedilir. Denetim çalışmadıysa sonuç “doğrulanamadı” kalır.
- Hafıza bounded ve şema sürümlüdür; kayıtlar hassas bilgi içermemeli ve saklama/temizleme politikası olmalıdır.

## Gizlilik ve şifreleme

“Şifreli” ve “ağda görünmez” aynı şey değildir. TLS bağlantı içeriğini aktarım sırasında korur; bağlantı uçları, zamanlama, boyut ve IP gibi meta veriler ağ gözlemcilerine görünebilir. Tam uçtan uca şifreleme ancak anahtarlar uçlarda tutulduğunda ve sunucu içeriği çözemediğinde mümkündür.

Önerilen katmanlar:

1. Yerel mod varsayılanı: sohbet, ses, görsel, video, hafıza ve kod yerel disk/yerel modellerle işlenir; uzaktaki yapay zekâ servisine sessiz geri dönüş olmaz.
2. Ağ modunda TLS 1.3; hassas kayıtlar için uygulama düzeyinde uçtan uca şifreleme ve kullanıcı cihazında tutulan anahtarlar. Anahtar kurtarma açık, anlaşılır ve kullanıcının kontrolünde olmalı.
3. Diskte şifreleme: işletim sistemi anahtar kasası veya doğrulanmış bir anahtar yönetim katmanı; anahtarları `.env`, log veya Git deposunda tutma.
4. Telemetri varsayılan kapalı; hata raporlarında kod/çıktı yerine redakte edilmiş parmak izi. Harici hava durumu/trafik sağlayıcısı kullanılırsa hangi konum verisinin gönderileceği kullanıcıya açıklanır.
5. GitHub bağlantısı en az ayrıcalıklı, depoya ve işleme göre sınırlandırılmış yetkilerle; token yalnızca secret store içinde tutulur. Ajanın görebildiği veriyi otomatik olarak herkese açık issue'lara veya PR'lara kopyalama.

## Güvenlik bulguları ve kötüye kullanım

- Savunmacı tarama yalnızca kullanıcı tarafından yetkilendirilmiş depolarda çalışır.
- Bulgu raporları güvenli varsayılanla özel kalır. Doğrulanmamış güvenlik açıkları, exploit adımları, sırlar ve hassas satırlar herkese açık issue/PR'a otomatik yazılmaz. Önce redaksiyon ve özel inceleme gerekir.
- Ajanın kendi zafiyetleri kullanıcıya güvenli bir yönetici panelinde, erişim kontrollü rapor olarak sunulur; bunlar herkese açık şekilde ifşa edilmez. Güvenlik bilgisini kullanıcıdan saklamak yerine yetkisiz kişilere sızmasını önlemek hedeflenir.
- Kötü amaçlı komutlar, kimlik bilgisi toplama, yetki yükseltme, korumaları atlatma veya üçüncü taraf sistemlere izinsiz erişim istekleri reddedilir.
- Kod/README/issue içindeki talimatlar güvenilmeyen veri kabul edilir; araç izinlerini veya sistem politikasını değiştiremez.

## Ses, görsel ve video

- **Bora**: mevcut yerel erkek Piper modeli için “tok, sakin, bilge ve güven veren” ürün profili.
- **Defne**: mevcut yerel kadın Piper modeli için “sıcak, net, akıcı ve enerjik” ürün profili.
- İsimler ve hız hedefleri ürün profilidir; doğal vurgu, doğru Türkçe telaffuz, nefes/prosodi ve insan benzerliği gerçek model dosyalarıyla ölçülmeden garanti edilemez. Bir Türkçe test korpusu, telaffuz ölçümü ve insan dinleme değerlendirmesi gereklidir.
- Görsel üretimi, görüntü düzenleme, video kare analizi ve metinden gerçek video üretimi farklı yeteneklerdir. Yalnızca yapılandırılmış yerel motorun sağlık kontrolü ve gerçek çıktı testi geçerse “hazır” gösterilir.
- Ses/görüntü dosyaları kullanıcı açıkça dışa aktarmadıkça uzaktaki servise gönderilmez.

## Hesaplar ve ücretsiz/ücretli model

İlk sürümde **hesapsız, tek cihaz/yerel kullanım** en güvenli ve anlaşılır varsayılandır. Hesap yalnızca cihazlar arası senkronizasyon, takım alanı veya uzaktan yönetim gerçekten gerektiğinde eklenmelidir.

- **Ücretsiz/yerel:** temel ajan, yerel ses profilleri, izinli proje denetimi, öğrenme hafızası ve kullanıcı cihazının kaldırdığı kadar yerel üretim.
- **Ücretli/ekip:** isteğe bağlı kendi sunucunda/self-hosted hızlandırma, çoklu kullanıcı rolleri, yönetim politikaları, daha uzun denetim geçmişi, kurumsal destek ve yönetilen yedekleme. Yerel modun temel gizlilik güvenceleri ücret duvarının arkasına konmamalı.
- Hesap gerekiyorsa passkey veya güçlü parola + Argon2id, MFA, oturum iptali, rate limit ve denetim günlüğü kullan. Şifreler geri çözülebilir biçimde saklanmaz. Kullanıcı hesabı, model sağlayıcısına veri gönderme izni anlamına gelmez.
- Ücretli bulut çıkarımı varsayılan olmamalı; ek bir işlemci kullanımı ancak açık opt-in, veri akışı açıklaması ve ayrı ayarla etkinleştirilmeli. Kullanıcı verileri reklam için satılmamalı.

## Hava durumu ve trafik

Bunlar yardımcı araçlar olmalı, ajanın çekirdeğine gömülmemelidir. Sağlayıcı adaptörleri, kaynak/tazelik zaman damgası, konum izni ve zaman aşımı içermeli. Hava durumu için Open-Meteo gibi bir sağlayıcı değerlendirilebilir; trafik sağlayıcısı ülke kapsamı, lisans, kota ve konum gizliliği açısından ayrıca seçilmelidir. İnternet kapalıysa son önbellek “eski veri” olarak işaretlenmeli; canlı veri varmış gibi gösterilmemelidir.

## Uygulama sırası

1. Öğrenme hafızası + gece yeniden kontrolü + regresyon testi kapısı.
2. Yerel PC köprüsü: salt okunur inceleme → açık onaylı dosya düzenleme → test çalıştırma → PR taslağı; otomatik `main` birleştirme yok.
3. Gerçek zamanlı durum olayları ve iptal/durdur kontrolleri.
4. Ses motoru için gerçek model sağlık kontrolü ve Türkçe telaffuz değerlendirmesi.
5. Yerel görsel/video motoru sağlık testleri ve üretim kanıtı.
6. Gizlilik/anahtar yönetimi denetimi; gerekiyorsa hesap ve ekip özellikleri en son.

Bu yol haritası gelecekteki işler için tasarımdır. Yukarıdaki maddelerin “mevcut” olduğu yalnızca kod ve test kanıtı bulunan bölümler için söylenebilir.
