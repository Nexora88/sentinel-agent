# Pinned candidate: SmolLM2-135M-Instruct

- Official repository: https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct
- Declared license: Apache-2.0 (verify the included LICENSE before redistribution).
- Immutable revision: 12fd25f77366fa6b3b4b768ec3050bf629380bac.
- Exact artifact URLs and the revision are recorded in model-lock.json.

## Hash status

The revision is pinned, but the binary SHA-256 values are intentionally null until the exact model/tokenizer files are downloaded and hashed. Never invent hashes. Run python tools/fetch_model.py --output-dir models/smollm2-135m-instruct/artifacts on a network-enabled machine and review the generated SHA256SUMS and model-lock.generated.json. Hashes verify artifact integrity, not license ownership or legal compliance.

Only safetensors and JSON files are in scope. Do not load or execute the repository's pickle-based training_args.bin.

## Compatibility gate

This is a real candidate model, not a currently supported Rust runtime model. SmolLM2 uses a Llama-style decoder with grouped-query attention and a BPE tokenizer/chat template. The current Rust decoder is a synthetic single multi-head block; ByteTokenizer is not compatible. The converter is format-only and does not provide architecture mapping. Do not claim inference compatibility until weights, tensor mapping, tokenizer output, and logits are validated against the official reference.

The model card says this model family primarily understands and generates English. Turkish quality must be measured. Ollama remains the fallback until identical prompt-set tests establish quality, stability, latency, and memory thresholds.
