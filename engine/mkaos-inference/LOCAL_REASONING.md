# MKAOS yerel akıl yürütme çekirdeği — başlangıç

Bu ilk aşama önceden eğitilmiş ağırlık, bulut API'si veya ağ çağrısı kullanmayan küçük bir Rust sembolik çıkarım motorudur. Üçüncü taraf LLM'den bilgi almaz. Henüz eğitilmiş bir sinir ağı veya genel amaçlı sohbet modeli değildir.

## Çalıştırma

    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- "12 * 3"
    cargo run --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-reason -- "Yağmur yağıyor ise yol ıslaktır. Yağmur yağıyor"

İz adımlarını görmek için MKAOS_REASON_TRACE=1 ortam değişkenini ayarla. PowerShell'de: $env:MKAOS_REASON_TRACE="1"

Komut satırına verilen metin yalnızca yerel süreçte işlenir. Kodda HTTP istemcisi, model indirme veya telemetri yoktur. Tam makine düzeyinde dışarı veri çıkışını engellemek için işletim sistemi güvenlik duvarı/ağ politikası gerekir; bu modül diğer süreçleri denetleyemez.

## İlk sürümün kapsadığı işler

- Temel tek işleçli sayısal ifadeler (+, -, *, /).
- Açık kural ve olgu üzerinden tek adımlı modus ponens: A ise B. A → Çıkarım: B.
- Hangi kuralın uygulandığını açıklayan kısa iz.
- Desteklenmeyen sorularda yanıt uydurmak yerine sınırını belirtme.

## Bilinçli sınırlar

- Türkçe doğal dili genel olarak anlayamaz; metindeki terimler kurallarda neredeyse aynı yazılmalıdır.
- Bellek, öğrenme, çok adımlı planlama, genel bilgi ve eğitilmiş dil üretimi henüz yoktur.
- Kaynak kodun bu projede yazılması tek başına tüm derleme zincirinin, işletim sisteminin veya donanımın yerli olduğu anlamına gelmez.
- Sonraki teknik aşamalar: yerel, sürümlenmiş bilgi/olgu deposu; kural çakışması yönetimi; Türkçe normalizasyon; ardından hakları temizlenmiş verilerle sıfırdan küçük bir nöral model eğitimi.
