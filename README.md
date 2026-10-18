-tr.jsonl --manifest ./approved-manifest.json --output-dir ./artifacts/mkaos-tr`
- Eğitim gereksinimi: yerel kurulumda PyTorch; hiçbir model deposuna veya indirme API'sine başvurulmaz.
- Çıktılar: `mkaos-owned.mkaosw`, `tokenizer.json` ve hash/seed/cihaz/kayıp bilgilerini içeren `training-report.json`.
- Yerel Rust CLI ile üretim: `cargo run --release --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-generate -- --checkpoint ./artifacts/mkaos-tr/mkaos-owned.mkaosw --sha256 <checkpoint_sha256> --heads 4 --kv-heads 2 --max-seq 128 --max-new-tokens 32 --prompt "Merhaba"` (baş/katman boyutlarını eğitim raporundan kullanın).
- Test bölümü optimizasyon ve model seçimi için kullanılmaz. Çalıştırma raporu Türkçe yetenek sertifikası değildir; bağımsız held-out değerlendirme ve Rust motorunda checkpoint yükleme/yanıt testi hâlâ gerekir.

Bu küçük byte-tokenizer modeli başlangıç araştırma hattıdır; üretim kalitesinde Türkçe asistan, GPU hızlandırması, dağıtık durum veya canlı mesh tamamlanmış sayılmaz.

## Open source worldwide

MKAOS is developed in public under the repository's MIT license. No institutional endorsement or certification is claimed. MIT applies to this repository's covered source; third-party model weights, datasets, voices, and assets may have separate terms. Public availability alone does not grant training or redistribution permission.

Read the current evidence and contribution policy in [MKAOS Open-Source Readiness](docs/MKAOS_OPEN_SOURCE_READINESS.md). The current source register contains **zero approved training sources**, so a real owned-model training run is not yet cleared to start. Host-metadata CI and ARM64 tests do not certify native inference on every platform. We will publish stronger claims only alongside reproducible evidence.

## MKAOS yerel sembolik akıl yürütme başlangıcı

Önceden eğitilmiş ağırlık veya ağ çağrısı olmadan çalışan küçük Rust başlangıç çekirdeği `engine/mkaos-inference/LOCAL_REASONING.md` içinde belgelenmiştir. `mkaos-reason` komutu temel aritmetik ve açık `A ise B. A` kuralından tek adımlı çıkarım yapar; genel amaçlı LLM değildir. Test etmek için `cargo test --manifest-path engine/mkaos-inference/Cargo.toml` komutunu çalıştır. Bu yeni çekirdek uygulama sohbet API'sinin model tabanlı yolunu değiştirmez.

## Hugging Face portability and offline hardening

The dependency-free, read-only local checkpoint inspector is `tools/mkaos_hf_adapter_preflight.py`; guide: [HF portability, output guardrails, PEFT and offline operation](docs/MKAOS_HF_PORTABILITY_AND_OFFLINE_SECURITY.md). It does not convert arbitrary `.safetensors` weights into `MKAOSW1`: architecture, tokenizer and numerical parity must be implemented and tested first. Final reasoning output now passes through a narrow local guard that redacts high-confidence credential-shaped strings; this is not a general fact-checker or model-safety certification. Dataset/model license, privacy, attribution and training approval gates remain mandatory.

The Hugging Face architecture decision table and required parity protocol are in [MKAOS HF compatibility matrix](docs/MKAOS_HF_COMPATIBILITY_MATRIX.md). A pinned SmolLM2-135M-Instruct CPU reference smoke workflow is defined at `.github/workflows/mkaos-hf-cpu-smoke.yml`. Its repeat-logit check validates the reference runtime only; it does not claim MKAOSW1 conversion parity. Numerical comparison metrics are implemented in `tools/mkaos_numerical_parity.py`.
