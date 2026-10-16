# MKAOS bağımsız Türkçe model: sürüm kapısı

Bu belge, sıfırdan eğitilmiş bir MKAOS modelinin araştırma denemesinden doğrulanabilir aday sürüme geçiş koşullarını tanımlar.

## Mevcut durum

- Rust MKAOSW1 checkpoint biçimini üreten sıfırdan eğitim aracı vardır.
- Eğitim aracı kaynak sicili ve manifest onayı başarısızsa eğitimi başlatmamalıdır.
- Rust motorundaki mevcut tokenizer UTF-8 bayt tokenizer'ıdır (0–255 + EOS). Türkçe karakterleri kayıpsız kodlar; ancak BPE/SentencePiece gibi Türkçe alt-kelime tokenizer'ı değildir.
- data/mkaos/source-register.json içinde current_approved_sources boş ve model_training_allowed false olduğundan gerçek korpus eğitimi şu an kasıtlı olarak engellenmiştir.
- Bu değişiklikte gerçek model checkpoint'i veya kalite iddiası yayımlanmıyor.

## Bu değişiklikteki doğrulama

`tools/evaluate_mkaos_turkish.py`, checkpoint'i doğrudan Rust `mkaos-generate` ikilisiyle çalıştırır, dosyanın SHA-256 değerini yeniden hesaplar, sabitlenmiş Türkçe smoke sorularını uygular ve sonuç/latency raporu üretir. Betik model indirmez, ağırlık değiştirmez ve raporu mevcut dosyanın üzerine yazmaz.

Örnek (önce gerçekten eğitilmiş bir checkpoint ve Rust ikilisi gerekir):

    cargo build --release --manifest-path engine/mkaos-inference/Cargo.toml
    python tools/evaluate_mkaos_turkish.py \
      --binary engine/mkaos-inference/target/release/mkaos-generate \
      --checkpoint artifacts/mkaos/model.mkaosw \
      --sha256 <GERCEK_64_HEX_SHA256> \
      --heads 4 --kv-heads 2 --max-seq 512 --max-new-tokens 48 \
      --report artifacts/mkaos/turkish-smoke-report.json

Bu smoke testi sadece çıkarım hattının çalıştığını ve birkaç beklenen kavramın çıktıda bulunduğunu denetler. **Tek başına akıl yürütme, doğruluk veya model kalitesi kanıtı değildir.** İnsan değerlendirmesi yapılmadığı sürece rapor `human_reviewed=false` ve `release_eligible=false` olarak kalır.

## Gerçek model için zorunlu kanıtlar

1. Kaynak ve lisans incelemesi: her kaynağın sabit sürümü, yerel dosya SHA-256'sı, eğitim ve ağırlık dağıtımı izni, atıf ve gizlilik kararı.
2. Eğitim korpusu: kaynak/belge bazında sızıntısız train/validation/test; tekrar, kişisel veri ve gizli bilgi denetimleri.
3. Tekrarlanabilir eğitim: Git commit'i, PyTorch/Rust sürümleri, seed, parametreler, veri manifest hash'i, eğitim günlüğü, validation kaybı ve bağımsız test raporu.
4. Checkpoint bütünlüğü: Rust biçimi, tüm tensor adları/şekilleri, sonlu ağırlıklar ve SHA-256 doğrulaması.
5. Tokenizer uyumu: eğitim ve Rust çıkarımındaki token ID'leri için aynı girişte golden-vector testleri. Türkçe BPE tokenizer'ına geçilecekse model vocab boyutu ve EOS kimliği de birlikte değiştirilmeli; sadece tokenizer dosyası eklemek yeterli değildir.
6. Türkçe değerlendirme: bağımsız test soruları, insan kör incelemesi, dil akıcılığı, olgusal doğruluk, matematik, çok adımlı akıl yürütme, kodlama, güvenlik, ezberleme/gizlilik, RAM ve gecikme.
7. Sürüm kartı: modelin gerçekten neyle eğitildiği, lisanslar, sınırlamalar, test sonuçları ve bilinen başarısızlıklar.

Küçük test verisiyle üretilmiş rastgele başlatmalı prototip, boru hattını sınayabilir; büyük model yeteneği iddiasına temel olamaz. Kaynak onayı ve gerçek korpus olmadan ağırlık üretmek yerine eğitim kapısını kapalı tutmak bilinçli bir güvenlik kararıdır.
