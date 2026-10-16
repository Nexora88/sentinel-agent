# MKAOS yerel akıl yürütme ve olgu belleği

Bu başlangıç motoru önceden eğitilmiş ağırlık, bulut API'si veya ağ çağrısı kullanmayan Rust sembolik çıkarım katmanıdır. Üçüncü taraf LLM'den bilgi almaz. Henüz eğitilmiş sinir ağı veya genel amaçlı sohbet modeli değildir.

## Çalıştırma

    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- "12 * 3"
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- "Yağmur yağıyor ise yol ıslaktır. Yağmur yağıyor"
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- "yağmur var ise yol ıslak. yol ıslak ise trafik yavaş. yağmur var"

Çıkarım izini görmek için `MKAOS_REASON_TRACE=1` kullan. PowerShell: `$env:MKAOS_REASON_TRACE="1"`.

## Yerel olgu belleği

Bellek varsayılan olarak çalıştırılan dizinde `mkaos-memory.tsv` dosyasında saklanır; dosya yolunu `--memory DOSYA` ile değiştirebilirsin. Bu dosya kullanıcıya aittir ve otomatik olarak Git'e eklenmemelidir.

    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- --memory ./private/mkaos.tsv --remember "hava=yağmurlu"
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- --memory ./private/mkaos.tsv --list-facts
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- --memory ./private/mkaos.tsv --conflicts
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- --memory ./private/mkaos.tsv --resolve "hava=yağmurlu"
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- --memory ./private/mkaos.tsv --forget "hava"

- Aynı özneye farklı bir değer kaydedilirse önceki değer silinmez; çelişki açıkça bildirilir.
- `--resolve` seçilen değeri tutar, diğer çelişkili değerleri kaldırır.
- `--forget` özneye ait tüm olguları siler.
- Olgular, çıkarım sırasında açık kural zincirleriyle eşleştirilebilir. Sistem kendiliğinden web'den bilgi toplamaz; belleğe yazılan bilginin doğru olduğunu da garanti etmez.
- Dosya biçimi UTF-8 metnini hex alanlar olarak saklar; JSON/üçüncü taraf veritabanı bağımlılığı yoktur.

## Kapsam ve gizlilik

- Temel aritmetik (+, -, *, /).
- Birden fazla kural boyunca sınırlı ileri zincirleme (en fazla 16 tur) ve döngü koruması.
- Türkçe büyük/küçük I/İ normalizasyonu ve açık olgu eşleştirmesi.
- Desteklenmeyen sorularda uydurma yanıt vermek yerine sınırını belirtme.
- Bu modülde HTTP istemcisi, model indirme veya telemetri yoktur. Ancak makinenin diğer süreçlerini kontrol etmez; tam cihaz çevrimdışılığı için işletim sistemi ağ politikası gerekir.
- Kaynak kodun bu projede yazılması tek başına tüm derleme zincirinin, işletim sisteminin veya donanımın yerli olduğu anlamına gelmez.

## Eğitilmiş checkpoint'i Rust'ta çalıştırma

`mkaos-run`, gerçek `MKAOSW1` dosyasını beklenen SHA-256 ile doğrular, yalnızca bu Rust decoder mimarisiyle şekil olarak uyumluysa yükler ve yerel KV-cache üretimi yapar:

    cargo run --release --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-run -- --checkpoint ./private-data/mkaos/run-001/model.mkaosw --sha256 <gercek-64-haneli-sha256> --prompt "Merhaba" --heads 4 --kv-heads 2 --max-new-tokens 64

Gerçek dosya yolu ve hash, eğitim raporundan alınmalıdır; örnek değer uydurma hash değildir. CLI çıktı metnini stdout'a, checkpoint hash'ini, üretilen token sayısını, süreyi ve yaklaşık token/saniyeyi stderr'e yazar. Hatalı hash, bozuk dosya veya uyumsuz tensor şekilleri reddedilir. Bu CLI'ın derlenmesi, gerçek eğitim checkpoint'inin mevcut olduğu anlamına gelmez; şu an repo içinde gerçek eğitim checkpoint'i yok ve kaynak onay kapısı kapalıdır.

## Sıfırdan nöral modelin durumu

Eğitim aracı rastgele başlangıç ağırlıklarıyla model oluşturmak üzere tasarlanmıştır; fakat kaynak sicilinde şu an ağırlık dağıtımına kadar doğrulanıp onaylanmış bir veri kaynağı yoktur. Kaynak izinleri, kişisel veri taraması, tam veri dosyalarının hash'leri ve ağırlık dağıtım koşulları doğrulanmadan gerçek eğitim başlatılmamalıdır. Sentetik test checkpoint'i gerçek eğitim sonucu değildir.

Sonraki kapı: kaynak bazlı onaylı veri → sıfırdan küçük model eğitimi → gerçek checkpoint SHA-256 doğrulaması → aynı checkpoint'i Rust decoder'a yükleme → bağımsız Türkçe testleri, kayıp/perplexity, doğruluk, RAM ve gecikme ölçümü.
