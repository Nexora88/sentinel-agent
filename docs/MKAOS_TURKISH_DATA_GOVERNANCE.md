# MKAOS Türkçe veri egemenliği ve eğitim yönetişimi

## Kapsam

Bu belge, Türkçe yazılım mühendisliği, savunmacı siber güvenlik ve kaynaklandırılmış kültürel/tarihsel bilgi için veri kabul politikasını tanımlar. Kurumların adı, verinin otomatik olarak serbestçe kullanılabileceği anlamına gelmez.

## Kabul kapıları

Her kayıt en az şu bilgileri taşımalıdır: `source_id`, `source_uri`, `license_id`, `consent`, edinim tarihi, içerik hash'i, dil, konu etiketi ve insan inceleme durumu. Kullanım izni belirsizse kayıt reddedilir veya açıklığa kavuşana kadar karantinada tutulur.

- Kamuya açık olmak, otomatik olarak telifsiz veya model eğitimine izinli olmak demek değildir.
- TTK, devlet arşivleri, üniversite ve akademik yayınların her birinin kullanım şartları ayrı incelenmelidir.
- Kişisel veri, sırlar, özel yazışmalar ve hassas bilgiler eğitimden önce yetkili ve belgelenmiş süreçle çıkarılmalıdır.
- Siber güvenlik örnekleri savunmacı kod inceleme, güvenli yapılandırma, CVE etkisinin anlaşılması, tespit ve düzeltme örüntülerini öne almalıdır.
- Tarihsel cevaplarda kaynak atfı, tarih/dönem bağlamı, güven düzeyi ve çelişen kaynak işareti bulunmalıdır.
- Kullanıcı geri bildirimi doğrudan ağırlıkları değiştirmez. Önce anonimleştirme, lisans/izin denetimi, insan incelemesi ve sabit test kümesinde değerlendirme gerekir.

## Sürümleme ve yayın

Her veri sürümü için manifest hash'i, kabul/red sayıları, kaynak/lisans dökümü, deduplikasyon yöntemi ve train/validation/test sayıları saklanır. Test kümesi eğitim ve prompt ayarlamasından ayrılır. Kritik güvenlik gerilemesi, tarihsel kaynak hatası veya gizlilik ihlali adayın yayınını durdurur. Yayın ve geri alma insan onayına bağlıdır.

Bu politika hukuki danışmanlık veya otomatik telif/kişisel veri tespiti garantisi değildir.
