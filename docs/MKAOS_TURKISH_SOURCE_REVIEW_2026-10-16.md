# MKAOS Türkçe kaynak incelemesi — 2026-10-16

Bu kayıt, resmî kaynak sayfalarının masa başı teknik incelemesidir; hukuki görüş, dosya hash'i, veri kümesinin içeriğinin bütünüyle temiz olduğu veya model ağırlıklarının dağıtımına izin verildiği anlamına gelmez. Hiçbir kaynak bu incelemeyle otomatik olarak onaylanmaz.

## Karar özeti

| Kaynak | Resmî kanıttan doğrulanan | Çözülmemiş risk | Bu incelemedeki karar |
|---|---|---|---|
| Mozilla Common Voice Scripted Speech v27.0 Turkish | Mozilla Data Collective ürün kaydı sürüm/ürün kimliği ve CC0 bildirimi sunuyor. Mozilla şartları, veri kümesinin yalnızca MDC üzerinden sunulduğunu ve yeniden barındırılmaması/paylaşılmaması gerektiğini söylüyor. Common Voice v27 datasheet'i Türkçe cümlelerin büyük çoğunluğunun Wikipedia kaynaklı olduğunu bildiriyor. | Wikipedia ve diğer üst kaynakların hak kapsamı; CC0 ile verilen dosyanın genel amaçlı üretken model eğitimi ve model ağırlığı dağıtımına uygulanması; tam indirilen dosya ve TSV hash'leri; kişisel veri/metadata taraması. | **Aday — kapalı**. Yalnızca yetkili MDC akışı; arşiv/TSV yeniden yayımlanmayacak. |
| Türkçe Wikipedia / Wikimedia metinleri | Wikimedia, metinlerin çoğunlukla CC BY-SA 4.0 ve/veya GFDL altında olduğunu, sayfa/ithal içerik istisnaları olabileceğini ve atıf/değişiklik yükümlülüklerini açıklıyor. | Tam dump sürümü ve sayfa bazlı istisnalar; ShareAlike/atıf koşullarının eğitim çıktıları ve dağıtılan model ağırlıklarına nasıl uygulanacağı; kişisel veri ve kaldırılmış içerik etkisi. | **Engelli — yazılı uyumluluk incelemesi gerekli**. |
| Tatoeba Türkçe metin | Resmî indirme sayfası metin dosyaları için genel olarak CC BY 2.0 FR bildiriyor; bazı cümleler için CC0 alt kümesi mevcut, ancak sayfadaki dil listesi Türkçeyi CC0 alt kümesinde göstermiyor. Ses lisansları katkı sahibi bazında değişiyor. | Tam export/satır bazında lisans ve yazar atfı; genel amaçlı model eğitimi ve ağırlık dağıtım uyumluluğu; cümle ve çeviri ilişkileri. | **Engelli — satır bazlı köken/atıf ve yazılı uyumluluk incelemesi gerekli**. Ses bu metin korpusuna dahil edilmemeli. |
| HPLT v2.0 cleaned Turkish (tur-Latn) | HPLT, paketlemenin CC0 olduğunu açıkça belirtiyor; aynı sayfa metinlerin kendisine ait olmadığını ve kullanıcının geçerli hukuka uymakla sorumlu olduğunu da belirtiyor. Türkçe temizlenmiş paket sayfada 426.16 GB olarak listeleniyor. | Çok büyük kaynak karışımı; her üst kaynağın hakları ve kişisel verisi; filtreleme/retention; dağıtılacak ağırlıklar için kapsamlı uyumluluk. Paket lisansı içeriklerin tümüne verilmiş izin sayılmaz. | **Aday — kapalı**. Tam arşivi otomatik indirme veya Git'e koyma yok; yalnızca kaynağı izlenebilir, onaylı bir alt küme düşünülebilir. |

## Resmî kaynaklar ve kanıt bağlantıları

1. **Common Voice ürün kaydı**: https://mozilladatacollective.com/datasets/cmu5wkah500c2o10719lem8m8
   - Kaynak sicilindeki kayıt: Common Voice Scripted Speech 27.0 Turkish, dataset ID cmu5wkah500c2o10719lem8m8.
   - Mozilla Common Voice yasal şartları (31 Ekim 2025 tarihinden itibaren): https://commonvoice.mozilla.org/dav/terms
   - Common Voice dataset sürüm metadata deposu: https://github.com/common-voice/cv-dataset
   - Common Voice kaynak açıklaması: https://github.com/common-voice/common-voice
   - Eylem: yetkili MDC akışıyla indirilen gerçek arşiv ve validated_sentences.tsv dosyasının SHA-256 değerlerini yalnızca yerel özel manifestte kaydet. Bu çalışma ortamında bu dosyalar yok; hash üretilmedi.

2. **Wikimedia metin lisansları ve tekrar kullanım**:
   - Wikimedia Foundation Terms of Use: https://foundation.wikimedia.org/wiki/Terms_of_Use
   - Wikimedia API content reuse: https://www.mediawiki.org/wiki/Wikimedia_APIs/Content_reuse
   - Eylem: exact dump/revision, sayfa geçmişleri, atıf ve ShareAlike/GFDL kapsamı hakkında yazılı karar alınmadan kaynak onaylanmamalı.

3. **Tatoeba indirme/lisans sayfası**: https://tatoeba.org/en/downloads
   - Tatoeba Türkçe SSS / atıf ve ses lisansları: https://tr.wiki.tatoeba.org/articles/show/sss
   - Eylem: exact export sürümünü sabitle; satır ID, katkıcı/yazar ve lisans alanlarını yerel audit kaydında koru. CC0 dosyasıyla metin genel dosyasını birbirine karıştırma; ses dosyalarını ayrı lisans kapısı olmadan kullanma.

4. **HPLT v2.0**: https://hplt-project.org/datasets/v2.0
   - Eylem: paket CC0 açıklamasını üst kaynakların tamamına verilmiş lisans gibi yorumlama. Tam paket indirmeden önce saklama kapasitesi, kaynak filtresi, kişisel veri denetimi ve hukuki inceleme planı hazırlanmalı.

## Teknik kanıtların mevcut durumu

- Resmî sayfa/lisans beyanları bulundu ve kaynak sicilindeki aday kayıtlarıyla karşılaştırıldı.
- Yerel arşiv/TSV dosyaları bu çalışma ortamında bulunmadığı için gerçek dosya SHA-256 değerleri **doğrulanamadı**.
- Satır düzeyinde kaynak kökeni, kişisel veri taraması ve belge-grubu train/validation/test ayrımı **yürütülmedi**.
- Model ağırlıklarının dağıtım koşulları için kaynak bazında yazılı hukuki onay **yok**.
- current_approved_sources boş, corpus_ready=false, model_training_allowed=false kalmalı.
- Bu yüzden gerçek korpusla sıfırdan eğitim, gerçek checkpoint üretimi ve bağımsız Türkçe kalite puanı **henüz yapılamaz**. Sentetik test fixture'ı gerçek korpus yerine geçmez.

## Onay kapısını açmak için gerekli somut kanıt

Her kaynak için tek tek:
1. Tam sürüm/revizyon, yetkili edinim yöntemi, gerçek dosya boyutu ve SHA-256.
2. Üst kaynakların ve istisnaların izlenebilir dökümü.
3. Eğitim kullanımına ve MKAOS checkpoint/ağırlıklarının planlanan dağıtımına dair belgeli insan/hukuk kararı.
4. Kişisel veri, gizli bilgi, telif/kaldırma talepleri, tekrarlar ve kaynak sızıntısı taramasının yerel raporu.
5. Atıf/ShareAlike gibi yükümlülüklerin nasıl yerine getirileceğini belirleyen kayıt.
6. Onaylı korpus manifestinin kaynak siciliyle birebir eşleşmesi.

Bu maddeler sağlandığında sonraki aşama: gerçek veride from-scratch eğitim → checkpoint ve tokenizer SHA-256 doğrulaması → aynı checkpoint'i Rust motoruna yükleme ve uçtan uca çıktı → önceden dondurulmuş bağımsız Türkçe testleri ve insan değerlendirmesi. Dosya bütünlüğü kontrolü, tek başına model kalitesi veya hukuki izin kanıtı değildir.
