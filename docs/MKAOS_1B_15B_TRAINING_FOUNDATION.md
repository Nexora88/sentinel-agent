# MKAOS Türkçe 1B–1,5B model eğitimi: altyapı planı

**Durum: altyapı geliştirme taslağı; henüz tam ölçekli eğitime hazır değil.** Bu belge bir eğitim çalıştırmaz ve herhangi bir veri kaynağını onaylamaz.

## Hedef

1. **Veri hazırlığı:** sürümü sabitlenmiş kaynaklardan yerel korpus üretimi, temizlik, tekrar/PII taraması, belge bazlı bölme, dosya SHA-256 değerleri ve kaynak manifesti.
2. **Hak ve kullanım kararı:** tam sürüm için eğitim izni, gizlilik/atıf koşulları ve model ağırlıklarının dağıtım izni ayrı ayrı insan tarafından karara bağlanır.
3. **Eğitim altyapısı:** parametre profili, bellek planlama, kararlı eğitim, devam ettirilebilir checkpoint, bağımsız test ve Rust biçimiyle uyumluluk.

## Ölçek profilleri

- `configs/mkaos/train-1b.json`: yaklaşık 1B sınıfı için model boyutları ve donanım planlama hedefleri.
- `configs/mkaos/train-1_5b.json`: yaklaşık 1,5B sınıfı için model boyutları ve donanım planlama hedefleri.
- `tools/plan_mkaos_training_scale.py`: parametre sayısı ve mevcut trainer'ın bellek tahminini raporlar; model tahsis etmez, veri indirmez ve eğitimi başlatmaz.

Profillerdeki `gradient_checkpointing` hedefi gelecekte uygulanacak bir gereksinimdir; mevcut trainer bu özelliği henüz uygulamıyor. Dağıtık eğitim ve optimizer-state sharding de henüz yok. Bu profiller bugün tek komutla 1B–1,5B eğitim çalıştırılabileceği anlamına gelmez.

## Donanım yaklaşımı

Büyük model için yalnızca parametre sayısı yetmez. AdamW parametre/gradient/optimizer durumları, aktivasyonlar, attention çalışma alanları, veri önbelleği ve checkpoint yazımı da bellek tüketir. Profildeki bellek hedefleri planlama değeridir, garanti değildir. Gerçek cihazın boş GPU belleği, sistem RAM'i, disk alanı ve BF16/FP16 desteği ayrı ölçülmelidir. Düşük RAM'li masaüstü sistemde tam 1B–1,5B eğitim gerçekçi kabul edilmez; önce kod/format pilotu, tam ölçekli eğitim için yeterli GPU veya kontrollü eğitim donanımı gerekir.

## Korpus ve haklar: şu anki durum

Türkçe Wikipedia/Wikimedia, Common Voice, Tatoeba ve HPLT kaynakları otomatik olarak onaylanmış değildir.

- Wikipedia için atıf, ShareAlike, sayfa geçmişi, alıntılar ve içe aktarılmış içerik ayrı incelenmelidir.
- Common Voice metin cümleleri ile ses dosyaları aynı hak kapsamına varsayılmamalıdır; tam sürüm ve dosya hash'leri gerekir.
- Tatoeba için katkı sahibi atfı ve cümle bazlı lisans farklılıkları korunmalıdır.
- HPLT paketinin kendi lisansı, içindeki her web metni için otomatik eğitim izni olarak yorumlanmamalıdır.

İnsan incelemesi olmadan `data/mkaos/source-register.json` içindeki `current_approved_sources` boş kalır ve eğitim kapısı kapalıdır. Lisansı “açık” olarak adlandırmak veya otomatik kontrolleri geçmek tek başına hukuki onay değildir. Eğitim izni verilse bile checkpoint'in yayımlanması ayrıca onaylanmalıdır.

## Bir sonraki mühendislik sırası

1. Sabitlenmiş korpus sürümünü indirme ve hazırlama işini tamamlamak; arşiv SHA-256, satır/split sayıları, hazırlama logu ve örneklem incelemesi raporunu kaydetmek.
2. Kaynak bazında hak/mahremiyet/atıf inceleme dosyasını tamamlamak; kararı, kanıt URL'sini, sürümü, dosya hash'ini ve inceleyen kişiyi kaydetmek.
3. Eğitim döngüsüne gradient checkpointing, checkpoint/resume, güvenli karma hassasiyet, optimizer-state kaydı ve deterministik devam eklemek.
4. Dağıtık eğitim veya optimizer-state sharding seçeneğini uygulamak.
5. Önce küçük pilotta loss eğrisi ve yeniden başlatma doğruluğunu incelemek; ardından 1B profili ve daha sonra 1,5B profili için donanım bazlı ölçüm yapmak.
6. Bağımsız test kümesi, Türkçe insan değerlendirmesi ve Rust checkpoint uyumluluğu olmadan kalite veya egemenlik iddiası yayımlamamak.

## Rapor üretimi

```bash
python tools/plan_mkaos_training_scale.py configs/mkaos/train-1b.json
python tools/plan_mkaos_training_scale.py configs/mkaos/train-1_5b.json --output artifacts/mkaos-scale-plan.json
```

Çıktı dosyası önceden bulunmamalıdır. Bu araç eğitim başlatmaz, hiçbir kaynağı onaylamaz ve hiçbir ağırlık üretmez.
