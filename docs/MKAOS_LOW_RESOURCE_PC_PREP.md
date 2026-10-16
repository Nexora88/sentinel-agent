# MKAOS low-resource PC preparation plan

**Status:** preparation guide only. This document does not install software, download a corpus, approve data rights, or start training.

## Hardware envelope

Target machine reported by the owner: older Intel i5, 8 GB RAM, approximately 40 GB free disk space, condition uncertain.

- Treat this machine as a data staging, validation, and small smoke-test machine first.
- Do not assume that it can train the 133M profile efficiently. The profile's 8 GiB minimum is a planning threshold, not a guarantee; the current approved cloud workflow intentionally requires a private GPU runner with at least 16 GiB system RAM and a GPU.
- Do not increase the parameter count just because the planned corpus is 30 GB. Corpus bytes, token count, parameter count, and training memory are different quantities. Select size only after tokenizer, data-quality, throughput, and held-out evaluation measurements.
- Do not store a 30 GB corpus on a drive with only 40 GB free. Keep at least 10–15 GB free for the OS, package caches, temporary files, logs, and checkpoints. Prefer a separate healthy drive with adequate capacity for the approved corpus and private checkpoints.

## Before installing anything

1. Confirm the operating system/version, CPU architecture, actual free disk space, RAM pressure, storage health, and whether the machine unexpectedly shuts down or overheats.
2. Back up important personal files before cleanup. Do not run destructive cleanup commands, delete unknown folders, repartition the drive, or disable system protections to make room.
3. Run operating-system updates and a reputable storage-health check. If disk errors, SMART warnings, repeated crashes, or thermal shutdowns appear, stop and repair the machine before training.
4. Install only the project runtime and dependencies needed for validation. Avoid installing a large local GPU/CUDA stack unless the machine actually has a supported discrete NVIDIA GPU; Intel integrated graphics should not be assumed to accelerate this training workflow.
5. Run the repository's tests and trainer preflight first. Never bypass the memory guard or run a long job unattended on an unreliable machine.

## Suggested staged use

### Stage A — inventory and health check

Record OS/version, CPU model, RAM available at idle, free disk space, disk-health status, and whether a supported discrete GPU exists. Do not download training data yet.

### Stage B — project setup and tiny smoke test

Clone the repository, create an isolated Python environment, install only the pinned project requirements, run unit tests, then use a small, rights-cleared sample to test parsing and the training preflight. Keep the corpus outside Git and do not commit datasets, credentials, model weights, or checkpoints.

### Stage C — data approval and storage

The source register must contain explicit approvals before the corpus is used. Verify each exact source release, its terms, privacy/PII screening, provenance, deduplication, train/validation/test separation, and the policy for distributing resulting weights. Do not turn on the training flags merely to make a workflow pass. Store the approved corpus and private checkpoints on a suitable private disk, not in a public repository or ordinary CI artifacts.

### Stage D — choose the training location

For this 8 GB RAM machine, prefer data validation and smoke tests locally. Use a genuinely free GPU runtime only if its current quota, session duration, persistent storage, privacy terms, and ability to run the project's code have been checked. A free hosted notebook is not the same as a persistent GitHub Actions runner. The existing `.github/workflows/mkaos-approved-training.yml` requires a separately registered self-hosted Linux x64 GPU runner; it does not provision or rent one automatically.

## Why 30 GB does not imply more parameters

A 30 GB text corpus can represent very different numbers of tokens depending on encoding, language mix, duplication, and tokenizer. With the current temporary byte tokenizer, Turkish characters can consume multiple byte tokens, wasting context. First compare a Turkish-capable subword tokenizer and measure token count, deduplication, validation loss, held-out Turkish task scores, throughput, and peak memory. Compare a smaller pilot with 133M under the same data and compute budget before considering a larger model.

## Safe go/no-go checklist

- [ ] Machine boots reliably; important files are backed up.
- [ ] Storage health checked; at least 10–15 GB remains free after setup.
- [ ] OS, CPU, RAM, and GPU details recorded.
- [ ] Repository tests and memory preflight pass.
- [ ] Exact corpus release and weight policy have written human approval.
- [ ] Corpus fits on a suitable private drive without exhausting free space.
- [ ] Small smoke test completes before any long training run.
- [ ] No private dataset, secret, checkpoint, or weight file is committed to Git.

**Current blocker:** the source register still has no approved sources and the training gate is closed. No corpus should be downloaded for training and no full training run should start until those approvals and the private runner/storage requirements are met.
