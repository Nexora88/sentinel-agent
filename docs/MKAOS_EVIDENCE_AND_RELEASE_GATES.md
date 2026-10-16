# MKAOS evidence and release gates

**Current state (2026-10-16): incomplete.** The repository contains an experimental, project-authored byte-level training path and a Rust inference implementation, but this does not mean a real approved corpus has been supplied, a trained owned checkpoint exists, or that checkpoint has passed Rust parity and Turkish quality tests.

## 1. Local archive and TSV integrity

Keep original archives, extracted source files, and the TSV inventory in a local data directory that is not committed unless redistribution has separately been approved. After placing the actual files there:

```bash
python tools/hash_mkaos_sources.py --root ./local-data/mkaos-sources --output ./local-data/mkaos-sources.sha256.tsv
python tools/hash_mkaos_sources.py --root ./local-data/mkaos-sources --verify ./local-data/mkaos-sources.sha256.tsv
```

The inventory includes each file's relative path, byte size, and SHA-256. The command also prints the SHA-256 of the inventory TSV itself. Re-run verification after copying or before training. Do not fill in made-up hashes: the files must exist locally. Hashes establish byte-level integrity only, not ownership, authenticity, licence, consent, or training permission.

## 2. Data-source and licence review

Use a separate record for each dataset/source and each material licence. Record the exact source URL/version, acquisition date, licence text/version, attribution obligations, commercial use and redistribution terms, source owner, evidence of permission/consent where needed, personal-data assessment, reviewer, review date, and decision. Do not infer training permission merely because a paper or archive is publicly readable.

For arXiv papers, review the specific paper's rights and any linked dataset/code licences separately; arXiv hosting is not a blanket licence for every paper or its referenced material. For Turkish archives, universities, public institutions, books and websites, review each collection's own conditions. A licence allowlist in code is a technical filter, not a legal opinion. Unclear sources remain quarantined and excluded.

Human/legal review is an external sign-off. This repository cannot honestly mark it complete automatically.

## 3. Corpus preparation and training

Once actual records are reviewed and approved, prepare a local JSONL dataset using `tools/prepare_mkaos_training_dataset.py`, retain its audit report and manifest hash, then run `tools/train_mkaos_owned_model.py` in an isolated development environment. Keep the exact git commit, manifest, command line, seed, environment, loss logs, validation metrics, checkpoint and checkpoint SHA-256 together.

The training script is a small byte-level research prototype. A successful run proves that a training loop executed on the supplied data; it does not prove broad Turkish competence, legal clearance, or production readiness. Never include private, sensitive, secret, or unreviewed material.

## 4. Rust checkpoint compatibility

A checkpoint must not be labelled Rust-compatible until the exact architecture and tokenizer are implemented in Rust and checked against a reference implementation. Save golden token IDs, logits with documented tolerances, generated outputs for fixed prompts, checkpoint/manifest hashes, and failure cases. Existing tests using third-party SmolLM2 weights or synthetic weights are useful separate checks; they are not evidence that the owned checkpoint works in Rust.

## 5. Independent Turkish evaluation

Use a fixed held-out test set that has not been used for training, prompt tuning or model selection. Include Turkish morphology and characters, factual QA with source requirements, instruction following, arithmetic, multi-step reasoning, coding, uncertainty/honesty, repetition, and safety. Record raw prompts and outputs, scorer/version, per-category scores, failures, sample count, model/tokenizer/checkpoint hashes, and hardware/software details. Have a human review a sample of outputs. String-contains checks are only smoke tests and cannot be reported as a full quality score.

## 6. Hardware and release evidence

Hardware is currently unknown. Record CPU model, RAM, OS, compiler/runtime versions, device availability, power/thermal limits where measurable, and exact commands. Measure cold and warm latency, p50/p95, generated tokens/s, peak memory, crashes and long-run stability on the actual target device. If hardware is unavailable, leave the field unverified.

Do not replace the currently configured comparison model or advertise a fully independent/competitive model until the approved corpus, real training run, checkpoint integrity, Rust parity, held-out Turkish results, and human release review are all evidenced. Missing evidence is a blocker, not a value to estimate.
