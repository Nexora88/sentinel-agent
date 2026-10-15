# MKAOS dependency governance and owned-model/Rust compatibility gates

## Dependency audit status

The local inventory is available without network access:

```bash
python tools/audit_dependencies.py --output artifacts/dependency-audit.json
```

It inventories direct Python requirements and the two Rust manifests, flags ranges that are not exact pins, and reports missing lockfiles. It deliberately does **not** claim to have checked vulnerability advisories or granted legal clearance. Those require current registry/security databases and human license review. To require exact pins and all expected lockfiles after the migration is complete:

```bash
python tools/audit_dependencies.py --strict
```

That strict command is expected to fail on the current repository until the dependency-lock migration is completed; do not suppress or re-label that result as a clean audit. Dependabot is configured for Python, both Rust crates, and GitHub Actions. Review updates rather than enabling blind auto-merge. In a network-enabled audit environment, run `pip-audit` and `cargo audit`, inspect transitive licenses and provenance, then commit the generated lockfiles and review the exact diff. Do not invent versions just to satisfy a pinning check.

## Critical model architecture mismatch

The current owned training prototype (`mkaos-byte-lm-v1`) is **not compatible** with the current Rust `GqaDecoder` or the existing MKAOSW1 tensor loader:

- Training uses a 256-token UTF-8 byte vocabulary, learned absolute position embeddings, PyTorch TransformerEncoder layers with pre-norm, GELU feed-forward blocks, LayerNorm, and tied embedding/output weights.
- The current Rust decoder uses a Llama-style decoder with RoPE, RMSNorm, GQA, and a SwiGLU feed-forward block. Its tokenizer contract includes EOS ID 256 and vocabulary size 257.
- The training script saves a PyTorch `.pt` state dictionary, while the Rust loader expects a hash-verified MKAOSW1 matrix container. A checkpoint hash alone does not make the formats or logits compatible.

Therefore no trained checkpoint may be loaded into the existing Rust decoder, and neither runtime replacement nor "sovereign/production-ready" status is permitted by this milestone.

## Required bridge before replacement

1. Choose and version a single architecture contract. Prefer changing the training prototype to emit a deliberately documented format and dimensions; do not silently reinterpret a `.pt` state dictionary as MKAOSW1.
2. Implement an exporter that validates every parameter name, shape, dtype, vocabulary size, positional scheme, normalization, activation and tied-weight rule before writing a new checkpoint.
3. Implement a matching Rust model path for that exact architecture (or deliberately retrain using the Rust decoder's architecture). Add a tiny deterministic golden checkpoint and golden token/logit vectors.
4. Test full-sequence logits against PyTorch within a declared tolerance, greedy token parity, UTF-8 boundary behavior, malformed/oversized checkpoint rejection, hash mismatch rejection, and context-length boundaries.
5. Run the same held-out Turkish/general evaluation set against the owned model and comparison models with fixed prompts and decoding settings. Publish results and limitations.
6. Only after quality, performance, memory and offline-egress gates pass may an owned checkpoint become a selectable candidate. SmolLM2 remains a comparison/temporary path until then; Ollama remains until local embedding/memory and offline behavior pass.

## Security and supply-chain release gate

- Keep model/data fetching out of normal runtime and training scripts.
- Review dependency license, current CVEs, transitive graph, maintainer/repository provenance and release signatures where available.
- Prefer lockfiles and reproducible builds; record toolchain and hashes.
- Verify network isolation externally; a JSON label or unit test alone cannot prove that the process had no network access.
- Treat benchmark reports as evidence only for the exact hardware, commit, dataset and configuration recorded in each report.
