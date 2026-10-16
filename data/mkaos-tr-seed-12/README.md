# MKAOS TR Seed-12

Bu dizin **proje tarafından yazılmış**, sentetik Türkçe eğitim örnekleridir.
Üçüncü taraf kitaptan, siteden veya model çıktısından kopyalanmamıştır.

## Lisans ve izinler

| Alan | Değer |
|------|--------|
| Lisans | CC0-1.0 (kamuya açık taahhüt; proje deposu MIT ile uyumlu) |
| AI / model eğitimi | **evet** — açıkça izinli |
| Ağırlık dağıtımı | **evet** — bu seed için izinli |
| Yayın / yeniden dağıtım | **evet** — metin dosyaları |
| Kişisel veri | **hayır** |

## Doğrulama zinciri

1. `python tools/verify_mkaos_twelve_texts.py --root data/mkaos-tr-seed-12`
2. İnsan onayı: `python tools/record_mkaos_human_approvals.py --ledger data/mkaos-tr-seed-12/approvals.jsonl --approve-all`
   (veya tek tek `--source-id` + `--decision approve|reject|needs_review`)
3. Kapı + eğitim + gerçek checkpoint SHA + Rust testi:
   `python tools/run_mkaos_turkish_twelve_gate.py`

Eğitim kapısı, 12 kaydın hepsi `approve` olmadan **açılmaz**.
Checkpoint SHA-256 dosyanın baytlarından hesaplanır; örnek/uydurma hash kabul edilmez.
