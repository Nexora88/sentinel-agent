# MKAOS: Kendi Modelini Geliştirme ve Kontrollü Öğrenme

Bu plan ve yardımcı modül, model eğitildi veya sertifikalandı demek değildir. Kod; veri kabulünü, veri kökenini ve sürüm yayın kapısını denetlenebilir hale getirir. Model ağırlıkları eğitimi, gerçek Ollama benchmark'ı ve bağımsız güvenlik incelemesi ayrı işlerdir.

## Tasarlanan döngü

1. **Yasal veri edinimi:** yalnızca lisansı doğrulanmış, kullanım amacı eğitim/değerlendirmeye uygun veya açık izin/consent kaydı olan veri. Kaynak kimliği, URL, lisans, tarih, izin ve veri sorumlusu kaydı saklanır. Belirsiz lisanslı, izinsiz, kişisel veya hassas kayıtlar varsayılan olarak reddedilir.
2. **Veri temizliği:** tekrarların içerik hash'iyle ayıklanması, kişisel/hassas bilgilerin yetkili süreçte temizlenmesi, dil/kalite etiketleri ve insan incelemesi. Bu yardımcı modül tam PII tarayıcısı değildir; redaksiyon ve veri koruma incelemesinin yerini almaz.
3. **Sızıntısız veri bölme:** aynı kaynaktan gelen kayıtlar train/validation/test bölümlerine birlikte atanır. Gerçek projede ayrıca konu, zaman ve kullanıcı/kurum ayrımıyla bağımsız holdout seti hazırlanır. Bölme küçük veri setinde boş test kümesi oluşturabilir; eğitim başlatmadan önce yeterli örnek ve kaynak sayısı doğrulanmalıdır.
4. **Başlangıç modeli ve uyarlama:** lisansı, ağırlık kullanım koşulları ve ticari/dağıtım hakları uygun bir temel model seçilir. Önce LoRA/QLoRA gibi geri alınabilir ince ayar denenir; sıfırdan büyük dil modeli eğitimi için veri, GPU, maliyet ve uzmanlık ayrı planlanır. Model adı/sürümü, temel ağırlık hash'i, tokenizer, eğitim kodu, hiperparametreler ve veri manifesti kaydedilir.
5. **Bağımsız değerlendirme:** Türkçe doğruluk, kod görevleri, talimat takibi, halüsinasyon, gizlilik, prompt injection, yetki sınırları ve kötüye kullanım senaryoları. Test kümesi eğitim veya prompt ayarlama sırasında kullanılmaz. Kritik güvenlik hatası varsa aday reddedilir.
6. **Aşamalı yayın:** aday mevcut kararlı sürümle aynı testlerde karşılaştırılır; kalite/latency gerilemesi ve kritik güvenlik hataları yayın kapısını kapatır. Sonuç raporu, model kartı ve insan onayı olmadan otomatik deploy yapılmaz. Geri alma sürümü hazır tutulur.
7. **Üretimden öğrenme:** kullanıcı konuşmaları varsayılan olarak eğitim verisi değildir. Açık, geri alınabilir kullanıcı izni, veri minimizasyonu, silme/retention politikası ve kimliksizleştirme olmadan eğitim kuyruğuna alınmaz. Üretim geri bildirimi önce anonimleştirilmiş değerlendirme adayı olur; ağırlıklar anında değiştirilmez.

## Bu PR'da uygulanan kod

- core/model_development.py: lisans/izin/kaynak alanları doğrulama, içerik hash'i, yinelenen örnekleri ayıklama, kaynağa göre kararlı split ve model adayı yayın kapısı.
- tests/test_model_development.py: izin/lisans reddi, tekrar kayıtlar, kaynak sızıntısı ve güvenlik/yayın kapısı testleri.

## Şu an uygulanmayan / doğrulanmayan işler

- Bu kod model ağırlıklarını eğitmez ve tek başına veri lisansının hukuki geçerliliğini doğrulamaz.
- Henüz lisans incelemesinden geçmiş büyük Türkçe veri kümesi, fine-tuning koşusu veya MKAOS'a özgü ağırlık yok.
- Gerçek Ollama modelleri bu GitHub CI ortamında çalıştırılmaz; gerçek kalite sıralaması ve tepe RAM/VRAM ölçümü donanım üzerinde ayrıca alınmalı.
- İstanbul–Ankara uçtan uca ağ testi, ortak işlemsel veri katmanı/failover ve FHE uygulaması ayrı altyapı çalışmalarıdır.
- ISO 27001, SOC 2 ve Common Criteria yalnızca kod ekleyerek kazanılmaz; kapsam, operasyonel kontroller ve bağımsız denetim/değerlendirme gerekir.

## Sonraki kabul kapıları

- En az iki değerlendiricili, körlenmiş ve dondurulmuş Türkçe test seti; sonuçların sürümlenmiş JSON/CSV raporu.
- Ayrı test makinesinde gerçek tepe RAM ve GPU bellek ölçümü (işletim sistemi + GPU sağlayıcısı metrikleri); ölçüm aracı ve donanım ayrıntıları rapora eklenir.
- İki ayrı düğümde gerçek mTLS taşıma katmanı; CA zinciri, iptal edilmiş sertifika, replay yarışı, yeniden başlatma, paket kaybı ve ağ kesintisi testleri.
- Çoklu düğüm için ortak işlemsel oturum/onay deposu, idempotency, failover ve geri yükleme tatbikatı.
- Eğitim verisi ve temel model lisans kontrolü; ayrı holdout; model kartı ve geri alma planı.
