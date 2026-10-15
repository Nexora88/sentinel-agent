# MKAOS bağımsız çıkarım motoru yol haritası

## Hedef ve dürüst durum

MKAOS'un uzun vadeli hedefi, model çalışma zamanı üzerinde mimari kontrolü artırmak ve Ollama gibi harici çalışma zamanlarına zorunlu bağımlılığı zaman içinde azaltmaktır. Bu, tek bir PR ile tamamlanmış değildir. İlk adım olarak `engine/mkaos-inference` altında harici crate bağımlılığı olmayan, `unsafe` kodu yasaklayan Rust CPU tensör çekirdeği başlatıldı.

**Mevcut kapsam:** temel matris çarpımı, satır bazlı kararlı softmax ve RMS normalizasyonu. Bu kod henüz tokenizer, transformer decoder, model ağırlığı yükleyicisi, KV cache, kuantizasyon, GPU sürücüsü veya sohbet üretim hattı içermez; mevcut Ollama yolunun yerine geçmez.

## Aşamalı plan

1. **Denetlenebilir çekirdek:** şekil/taşma/NaN kontrolleri, deterministik CPU işlemleri, birim testleri ve referans sonuçlarla karşılaştırma.
2. **Model sözleşmesi:** sürümlü ve açık dokümante edilmiş model manifesti; tensör adları/şekilleri, tokenizer kimliği, ağırlık hash'leri, sayısal tür ve lisans/menşe alanları.
3. **Tokenizer ve küçük referans model:** küçük, açık lisanslı bir test modeliyle uçtan uca tokenleştirme ve üretim; mevcut model aileleriyle uyumluluk ancak lisans ve format incelemesinden sonra.
4. **Transformer bileşenleri:** embedding, RoPE, attention, KV cache, MLP/SwiGLU, RMSNorm ve örnekleme. Her bileşen Python/başka referans uygulamayla diferansiyel teste tabi tutulmalı.
5. **Bellek ve performans:** F32 doğruluğu, sonra F16/BF16/INT8/INT4 gibi türler için ölçümlü optimizasyon. SIMD ve GPU/NPU yolları yalnızca gerçek cihaz benchmark'ı varsa desteklenmiş ilan edilir.
6. **Model uyarlama:** önce izinli veri ve uygun lisanslı temel ağırlık üzerinde LoRA/QLoRA; sıfırdan temel model eğitimi ayrı GPU/veri/uzmanlık bütçesi ister.
7. **Kontrollü sürekli gelişim:** üretim konuşmaları varsayılan olarak eğitim verisi olmaz. İzin, kaynağın lisansı, kişisel veri temizliği, insan değerlendirmesi ve sabit holdout testleri gerekir. Aday ağırlıklar otomatik olarak kararlı sürümün üzerine yazılmaz.
8. **Kademeli bağımsızlık:** aynı sabit değerlendirme kümesinde doğruluk, güvenlik, RAM/VRAM, gecikme ve enerji ölçümleri karşılaştırılır. Bağımsız motor eşit veya daha iyi sonuçları tekrarlanabilir biçimde verene kadar mevcut backend geri dönüş seçeneği olarak kalır.

## Türkçe ve kültürel veri egemenliği

- Kaynaklar kurum adıyla değil, her bir veri kaydının somut URL/kimlik, tarih, lisans/kullanım izni ve bütünlük hash'i ile kayıt altına alınır.
- Türk Tarih Kurumu, devlet arşivleri ve akademik yayınlar için toplu veri alma veya eğitim izni varsayılmaz; her kaynağın telif, erişim şartları ve yeniden kullanım koşulları ayrı doğrulanır.
- Tarihî olgulara mümkün olduğunda birincil kaynak, kaynaklar arası çapraz kontrol, dönem bağlamı ve güven düzeyi eklenir. Tartışmalı iddialar olgu gibi etiketlenmez; kaynak gösterimi model değerlendirmesinin parçasıdır.
- Eğitim veri seti kaynak ve lisans bazında bölünür; aynı kaynaktan gelen metinlerin train/test'e dağılmasıyla oluşabilecek sızıntı önlenir.
- Kullanıcı konuşmaları açık izin ve belgelenmiş saklama/silme politikası olmadan eğitime alınmaz. Veri seti manifesti ve reddedilen kayıt raporu sürümlenir.
- Kumru AI veya başka Türkçe modellerle olası entegrasyon/ortaklık, teknik uyumluluk ve lisans koşulları incelenmeden var kabul edilmez.

## Güvenlik ve çevrimdışı çalışma

- Derleme ve testler ağ erişimi gerektirmemelidir; bağımlılıksız Rust çekirdeği bu hedef için başlangıç noktasıdır.
- Air-gapped iddiası yalnızca uygulama ayarıyla değil, işletim sistemi/firewall, konteyner ağı, DNS/egress denetimi ve gözlemlenebilir ağ testleriyle doğrulanır.
- Siber güvenlik verileri savunmacı kullanım, izinli laboratuvar senaryoları, güvenli yama ve kod inceleme odaklı seçilir; gerçek hedeflere izinsiz saldırı yönergeleri eğitim hedefi yapılmaz.
- Model cevapları güvenlik kararı veya tarihsel doğruluk garantisi sayılmaz; kaynak, belirsizlik ve insan doğrulaması gerekir.

## Katkı ve araştırma iş akışı

Her yeni kernel için: (1) matematiksel tanım, (2) sınır koşulları, (3) referans test, (4) CPU benchmark, (5) güvenlik incelemesi, (6) model lisans/menşe kontrolü eklenir. İyileştirme önerileri ölçüm raporuyla açılır; performans iddiası gerçek donanımda tekrarlanabilir sonuç olmadan yapılmaz.
