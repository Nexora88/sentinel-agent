# Pinned candidate: SmolLM2-135M-Instruct

- Official repository: https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct
- Declared license: Apache-2.0 in the pinned model-card metadata; inspect the license text and notices before redistribution.
- Immutable revision: `12fd25f77366fa6b3b4b768ec3050bf629380bac`.
- Exact artifact URLs and the revision are recorded in `model-lock.json`.

## Hash status

The committed `model-lock.json` contains measured SHA-256 values for the pinned weights and tokenizer files. The lock records that those hashes were measured against the immutable revision in GitHub Actions run 38778224914. This verifies byte identity for the tested artifacts; it does not prove authorship, legal clearance, Turkish quality, or device performance.

The model weights and tokenizer binaries are intentionally not committed to this checkout. On a network-enabled machine with sufficient storage, retrieve the pinned files with:

```sh
python tools/fetch_model.py --output-dir models/smollm2-135m-instruct/artifacts --lock-file models/smollm2-135m-instruct/model-lock.json
```

Review the downloaded files against the lock before inference. Never replace measured hashes with estimates. The downloader streams files with per-artifact byte limits and is pinned to the immutable revision.

Only safetensors and JSON/text files are in scope. Do not load or execute pickle-based `training_args.bin`.

## Compatibility gate

The mkaos-hf-adapter crate maps standard Llama tensor names and F32/F16/BF16 SafeTensors values into the multi-layer GQA decoder; mkaos_generate and mkaos_logits are available as local binaries. The existing ByteTokenizer remains incompatible with this model; use the Hugging Face tokenizer.json adapter. The pinned tokenizer and real-weight logits checks passed for the tested cases in GitHub Actions run 38778224914. This is bounded numerical compatibility evidence, not proof of general generation quality, full context behavior, or local-device performance. Re-run the checks after any loader, tokenizer, or model revision change.

The model card describes the model as primarily English. Turkish quality must be measured. tools/benchmark_mkaos_vs_ollama.py provides a same-device prompt runner, but has not been run against real artifacts here. Ollama remains the fallback until identical prompt-set tests establish quality, stability, latency, and memory thresholds.
