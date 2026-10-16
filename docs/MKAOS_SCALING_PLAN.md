# MKAOS scaling, hardware, and offline retrieval plan

## Current reality

- The training script builds a decoder from random initialization; no pretrained weights are downloaded.
- Training now accepts --device auto|cpu|cuda and --precision auto|fp32|fp16|bf16. The CUDA PyTorch API is also the API exposed by ROCm-enabled PyTorch builds; the report distinguishes ROCm using torch.version.hip.
- Automatic device discovery is not proof that the Rust inference engine supports that accelerator. Rust inference remains CPU-only until a backend adapter is implemented and numerically validated.
- The local machine observed for this work has an Intel UHD integrated graphics adapter (reported 1 GiB shared/reserved adapter memory), about 3.9 GiB visible RAM, about 0.58 GiB free physical memory at probe time, and about 6.12 GiB free on C:. This is suitable for lightweight code work, not 1B–3B training or storing the raw Wikipedia dump plus prepared splits.
- The corpus workflow belongs on cloud runners. It publishes a report/manifest by default and does not retain the prepared corpus or model weights by default.

## Memory planning

The training preflight uses a conservative planning estimate:
- 16 bytes per parameter for FP32 weights, gradients, and AdamW state;
- an approximate activation allowance based on batch size, sequence length, hidden size, layer count, and intermediate size;
- a refusal if the estimated requirement exceeds 80% of currently available system RAM or accelerator memory.

This is an estimate, not a peak-memory guarantee. CUDA/ROCm allocator overhead, kernels, attention workspaces, data buffers, fragmentation, and OS activity can raise actual usage.

Indicative configurations for the current byte-token decoder (actual counts are emitted by the script):

| Target scale | Example architecture | Parameter-memory floor | Practical planning |
|---|---|---:|---|
| ~1B | hidden 2048, 24 layers, 16 query heads, 4 KV heads, intermediate 5504 | ~16 GiB for FP32 parameters + gradients + AdamW states | Start with a verified 32 GiB+ GPU/accelerator, micro-batch 1, short sequence; profile before increasing |
| ~3B | hidden 2048, 48 layers, 16 query heads, 4 KV heads, intermediate 8192 | ~48 GiB for FP32 parameters + gradients + AdamW states | Plan for 64 GiB+ accelerator memory or implement and validate distributed/sharded training first |

These are planning examples, not trained checkpoints or guaranteed hardware minima. The current script does not implement distributed training, optimizer-state sharding, activation checkpointing, or 8-bit optimizers. Do not try a 1B–3B run on a 4 GiB RAM laptop. Parameter count alone also does not make the byte-token model linguistically competent; byte-level tokenization is data-inefficient for natural-language pretraining.

## Example: inspect a configuration before training

    python -m unittest tests.test_hardware_backends -v
    python tools/train_mkaos_from_scratch.py --help

Use the real training CLI only after the source register and data manifest pass their review gates, the corpus has adequate train/validation/test content, and the target machine has been verified. Example flags for a future reviewed dataset:

    python tools/train_mkaos_from_scratch.py --corpus <approved-local-corpus.jsonl> --manifest <reviewed-manifest.json> --source-register data/mkaos/source-register.json --output-dir <private-output-directory> --device auto --precision auto --batch-size 1 --gradient-accumulation-steps 16 --sequence-length 512

Do not run the example with placeholders. The source register remains unapproved until source-specific rights, privacy, attribution, and quality review is documented. Weight redistribution is a separate approval.

## Retrieval and memory

- mkaos-native is a deterministic local word/character n-gram hashing baseline. It is offline and dependency-light, but is not a trained semantic model.
- local-semantic loads a Sentence-Transformers model from an existing local directory with local_files_only=True and trust_remote_code=False. It never downloads weights. Install a model only after separately reviewing its source license, privacy implications, exact files, and SHA-256 inventory.
- To inventory an already-installed model without copying or downloading it, run tools/hash_local_embedding_model.py --model-dir <local-model-dir> --output <inventory.json>; later verify with --verify <inventory.json>. This proves file identity only, not legal clearance or semantic quality.
- SEKA_REQUIRE_SEMANTIC_EMBEDDINGS=true can fail closed when the local semantic model is missing; do not silently claim semantic quality while running the hash baseline.
- Different embedding providers use different collection suffixes to prevent vectors from incompatible embedding spaces being mixed. Tenant-scoped retrieval remains required.
- The synthetic retrieval benchmark is a smoke test only. Compare providers against the same fixed corpus and reviewed relevance labels; record Recall@k, MRR, nDCG, latency, memory, offline behavior, restart persistence, and tenant isolation.

## Test order for the next milestone

1. Complete the corpus workflow and inspect the generated manifest and hashes.
2. Review source rights/privacy and approve exact source releases explicitly; do not infer approval from a successful download.
3. Implement and validate the Rust accelerator adapter separately from PyTorch training discovery.
4. Select a local semantic embedding model only after provenance review and verify that no network access occurs during retrieval.
5. Run the second comprehensive test pass after code changes are complete: unit/regression tests, Rust tests, CPU baseline, accelerator tests only on matching hardware, retrieval benchmark, offline egress test, and tenant-isolation checks.
6. Publish measured numbers and their hardware/configuration; never report a test that was not run or treat a loss value as proof of useful Turkish reasoning.
