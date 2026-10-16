# MKAOS Türkçe Bağımsızlık Mücadelesi

**Slogan yönü:** Yerel motor · onaylı Türkçe veri · gerçek hash · sessiz yabancı yedek yok.

Bu belge motivasyon metni değil; **ölçülebilir kapılar** listesidir.

## Bugün nerede (dürüst durum)

| Katman | Durum |
|--------|--------|
| Rust çıkarım motoru | Var (`engine/mkaos-inference`) |
| HTTP sohbet → native-rust | Var; checkpoint yoksa **503** (fail-closed) |
| Üçüncü taraf sessiz fallback | Kapalı |
| Türkçe seed + SHA + insan onayı | `data/mkaos-tr-seed-12` + batch2 (24 örnek) |
| Eğitim boru hattı | Var (`train_mkaos_rust_compatible.py`) |
| Kullanılabilir büyük Türkçe model | **Henüz yok** |
| Held-out insan kalite skoru | **Henüz yok** |

“Yüzde yüz Türk sistem” = yalnızca arayüz dili değil; **veri menşei + eğitim + çıkarım + dağıtım** zincirinin yerelleşmesi.

## Kapı sırası

### K1 — Veri egemenliği
1. Kaynak URI, içerik SHA-256, lisans, AI/eğitim/yayın izni.
2. İnsan kararı: `approve` / `reject` / `needs_review`.
3. Kapı kapalıyken eğitim yok.

```bash
python tools/merge_mkaos_turkish_seeds.py
python tools/verify_mkaos_twelve_texts.py --records data/mkaos-tr-seed-12/records_all.jsonl
python tools/record_mkaos_human_approvals.py --records data/mkaos-tr-seed-12/records_all.jsonl --approve-all
python tools/run_mkaos_turkish_twelve_gate.py --auto-approve
```

### K2 — Rastgele başlangıçtan eğitim
- Onaylı manifest, train/val/test kaynak sızıntısız.
- Checkpoint SHA-256 **dosyadan** hesaplanır.

### K3 — Rust yükleme
- Aynı ağırlık `.mkaosw` olarak export.
- SHA eşleşmeden üretim yok.

### K4 — Kalite (açık)
- Held-out Türkçe görevler, insan incelemesi.
- Tek seed modeli “genel Türkçe zekâ” ilan edilmez.

### K5 — Varsayılan sohbet
- `MKAOS_NATIVE_CHECKPOINT` + `MKAOS_NATIVE_SHA256` doldurulunca native yol açılır.
- Ollama yalnızca bilinçli legacy profil.

## Dil politikası

`core/language_policy.py`:
- Varsayılan çerçeve Türkçe.
- Eğitim kayıtlarında Türkçe sezgisi.
- Native chat istemi `Kullanıcı` / `MKAOS` şablonuyla sarılır.

## Bir sonraki somut adımlar

1. Seed’i 24 → yüzlerce **izinli** orijinal veya CC0/CC-BY Türkçe çifte genişlet (aynı gate).
2. Gece işi: yalnızca onaylı kaynaklardan aday kayıt üret; otomatik approve **yok**.
3. Held-out benchmark: `benchmarks/mkaos-quality-tr-001.json` üzerinde insan notu.
4. Eğitilmiş checkpoint’i `models/mkaos/` altına koy; SHA’yı `.env`’e yaz; 503’ten çık.

## Kırmızı çizgiler

- Uydurma hash / örnek SHA yok.
- Onaysız web kazıntısı eğitim setine girmez.
- “%100 Türk” iddiası kalite kanıtı olmadan pazarlanmaz.
