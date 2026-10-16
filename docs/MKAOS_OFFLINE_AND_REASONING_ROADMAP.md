# MKAOS çevrimdışı çalışma ve yerli model yol haritası

Bu belge bir hedef ve uygulama sırasıdır; tamamlanmamış bir yeteneği tamamlandı gibi sunmaz.

## Bu aşamadaki somut değişiklik

- Yerel RAG, mevcut yerel vektör/özellik-hash aday sıralamasını küçük bir BM25 tarzı sözcüksel puanla birleştirebilir.
- Reranker deterministiktir; ağ erişimi, dış API, indirilen ağırlık veya yeni çalışma zamanı bağımlılığı kullanmaz.
- Bu, **hibrit sözcüksel yeniden sıralamadır; semantik embedding değildir**. Eş anlamlı/parafraz sorgularının güvenilir biçimde anlaşılması için ayrıca izinli verilerle eğitilmiş veya kullanım/lisansı onaylanmış yerel embedding modeli ve bağımsız retrieval değerlendirmesi gerekir.
- RAG belge/tenant sınırları, saklama limitleri ve başarısızlıkta boş sonuç davranışı korunur.

## Gerçek çevrimdışı kullanım kontrol listesi

1. Çevrimiçi hazırlık makinesinde uygulama imajını ve gereken model dosyalarını güvenilir kaynaktan edin.
2. Eğitim verisi/manifest kaynak register, lisans, gizlilik, PII ve train/validation/test kapılarından geçmeden gerçek MKAOS eğitimini başlatma.
3. Her model, tokenizer, ses paketi ve uygulama imajı için sürüm + SHA-256 manifesti oluştur; imzalı/kurumsal onaylı artefaktları kullan.
4. Model dosyalarını models/ altına kopyala; model ağırlıklarını Git deposuna veya loglara koyma.
5. docker-compose.offline.yml ile internal: true ağı kullan ve ana makine firewall'ında da çıkışı engelle. Compose ağı ana makinenin diğer süreçlerini izole etmez.
6. İnternet kesikken /health, giriş, yerel sohbet, yerel dosya RAG'i, kalıcı bellek ve ses özelliklerini ayrı ayrı test et. Bir ağ engeli testi tek başına tüm veri çıkışının imkânsız olduğunu kanıtlamaz.

## Kurulum zorluğunu azaltma sırası

- Önce tek komutlu, salt-okunur kurulum denetimi: sürüm, gerekli dosya, hash, izin ve çevrimdışı Compose yapılandırmasını kontrol etmeli; kendiliğinden model indirmemeli.
- İlk sahip parolası: sadece yerel dosyada tutulan sır için açık docker compose exec ... cat ... komutu; parola loga, API yanıtına veya telemetriye yazılmamalı. Üretimde OWNER_PASSWORD bir sır yöneticisiyle sağlanmalı.
- İsteğe bağlı medya bağımlılıkları temel sohbet kurulumundan ayrılmalı; Piper, Whisper, görsel ve video bileşenleri ancak kullanıcı etkinleştirirse kurulur.
- Model hazırlama profili ile interneti kapalı çalışma profili farklı tutulmalı. down -v komutu, kalıcı model hacimleri için önerilmemeli.

## Yerli temel model ve saf akıl yürütme planı

### A. Veri egemenliği
- Her kaynak için insan tarafından doğrulanmış eğitim ve yeniden dağıtım izni, kaynak snapshot'ı, SHA-256, PII incelemesi ve split kaydı gerekir.
- Şu anda onaylı kaynak sayısı sıfırsa eğitim bloklanmış kalmalıdır. Bu kapı gevşetilmemeli.

### B. Küçük donanımda temel model araştırması
- Önce küçük byte/alt-kelime tokenizer karşılaştırması; tokenizer değişikliği checkpoint biçimi ve Rust çıkarım sözleşmesiyle birlikte sürümlenmelidir.
- Bellek kısıtlı eğitim için mikro-batch, gradient accumulation, mixed precision yalnızca cihaz destekliyorsa, checkpoint/resume ve deterministik öğrenme oranı planı ölçülmelidir.
- Eğitim/validation/test veri sızıntısı engellenmeli; test kümesi yalnızca model seçimi bittikten sonra bir kez değerlendirilmelidir.
- Loss düşüşü tek başına akıl yürütme değildir. Çok adımlı mantık, matematik, Türkçe anlama, kod, güvenli davranış ve karşı-örneklerden oluşan sabit görev seti; insan incelemesi ve tekrar üretilebilir rapor gerekir.

### C. Bağımsız yerel semantik arama
- İlk hedef: izinli Türkçe çiftler ve zorlu negatiflerle küçük embedding modelini eğitmek veya açıkça lisanslanmış bir yerel modeli seçmek.
- Değerlendirme: Recall@k, MRR/nDCG, paraphrase ve Türkçe ekli sözcük testleri, kaynak/tenant izolasyonu ve CPU/RAM gecikmesi.
- Kalite eşiği karşılanana kadar hibrit arama açıkça deneysel olarak etiketlenir.

### D. Bağımsızlık iddiası için kanıt
- Üçüncü taraf ağırlık, tokenizer, embedding, ses modeli ve indirme adımları ayrı ayrı envanterlenir.
- “Yüzde yüz yerli/bağımsız” iddiası ancak tüm model ağırlıkları ve tokenizer menşei, lisans, derleme zinciri, ağsız çalışma ve bağımsız değerlendirme kanıtlandığında yapılır.
- Bu repo aşamalı geçiştir; mevcut deneysel küçük modelin frontier sistemlerle aynı saf zekâ seviyesinde olduğu iddia edilmez.
