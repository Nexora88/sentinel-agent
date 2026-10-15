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

This is a real candidate model, not a currently supported Rust runtime model. SmolLM2 uses a Llama-style decoder with grouped-query attention and a BPE tokenizer/chat template. The existing `ByteTokenizer` is not compatible. The safetensors converter is a format converter, not a model architecture mapper. Do not claim inference compatibility until the exact weights, tensor mapping, tokenizer output, and logits have been validated against the official reference.

The model card describes the model as primarily English. Turkish quality must be measured. Ollama remains the fallback until identical prompt-set tests establish quality, stability, latency, and memory thresholds.
