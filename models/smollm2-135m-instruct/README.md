# Pinned candidate: SmolLM2-135M-Instruct

- Official repository: https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct
- Declared license: Apache-2.0 in the pinned model-card metadata; inspect the license text and notices before redistribution.
- Immutable revision: `12fd25f77366fa6b3b4b768ec3050bf629380bac`.
- Exact artifact URLs and the revision are recorded in `model-lock.json`.

## Hash status

The immutable revision is pinned, but the committed binary SHA-256 values remain null until the exact files have been downloaded and hashed. Never invent hashes. On a network-enabled machine, run:

```sh
python tools/fetch_model.py --output-dir models/smollm2-135m-instruct/artifacts --lock-file models/smollm2-135m-instruct/model-lock.json
```

Review the generated `SHA256SUMS`, compare the resulting lock-file diff, and commit the measured values. Hashes verify artifact integrity, not authorship or license compliance. The downloader streams files with per-artifact byte limits and is pinned to the immutable revision.

Only safetensors and JSON/text files are in scope. Do not load or execute pickle-based `training_args.bin`.

## Compatibility gate

This is a real candidate model with a newly added but not yet validated Rust loading path. The mkaos-hf-adapter crate now maps standard Llama tensor names and F32/F16/BF16 SafeTensors values into the multi-layer GQA decoder; mkaos_generate and mkaos_logits are available as local binaries. The existing ByteTokenizer remains incompatible with this model; use the Hugging Face tokenizer.json adapter. Do not claim inference compatibility until the exact files are downloaded and tools/validate_tokenizer.py plus tools/validate_model_logits.py pass against the official reference.

The model card describes the model as primarily English. Turkish quality must be measured. tools/benchmark_mkaos_vs_ollama.py provides a same-device prompt runner, but has not been run against real artifacts here. Ollama remains the fallback until identical prompt-set tests establish quality, stability, latency, and memory thresholds.
