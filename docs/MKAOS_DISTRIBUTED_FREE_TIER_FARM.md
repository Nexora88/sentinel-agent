# MKAOS distributed free-tier storage and training farm

**Status: design proposal only. No cloud accounts, buckets, GPU sessions, or training jobs have been created.** This plan must not bypass provider quotas, create duplicate accounts to evade limits, or assume free capacity is guaranteed.

## Objective

Build a small, provider-neutral farm that can store a corpus in verified shards, run short training jobs on whichever compliant compute is available, and continue later from a durable checkpoint. The old i5 PC is optional and may remain offline.

## Important distinction: storage vs compute

- **Storage capacity is not training capacity.** 100 GB stored across services does not provide a GPU, RAM, CPU time, or uninterrupted execution.
- A powered-off PC does no work. A later cloud session can continue only if corpus shards and a compatible full-state checkpoint are stored durably and resume code passes tests.
- Free-tier quotas change and may be unavailable. Do not guarantee 100 GB free before checking current terms, actual quotas, retention, egress limits, and persistence.
- Do not create or rotate multiple accounts to evade quotas, use services contrary to their terms, or keep sessions alive through workarounds. Use legitimate accounts and provider-approved usage.
- Avoid splitting a single training step across unrelated notebook providers. Initially run one job at a time on one worker; move between providers only at tested checkpoint boundaries.

## Proposed architecture

1. **Corpus registry (metadata only in Git):** source IDs, rights-review status, version, per-shard SHA-256, byte count, record count, tokenizer version, and split assignment. Never commit the corpus, credentials, access tokens, or private checkpoints to Git.
2. **Private shard storage:** divide approved data into deterministic compressed JSONL shards (for example, 256 MiB–1 GiB each, adjusted after testing). Use a storage adapter per provider. A manifest records shard locations; verify each download against SHA-256 before use.
3. **Single job coordinator:** maintain a durable run manifest with a unique run ID, code/config/tokenizer/data hashes, completed shards, global step, last checkpoint, and provider status. Select only providers whose terms, quota, and hardware fit the job. Do not automatically upload sensitive data to a new provider.
4. **Preflight before every session:** verify approved corpus, free disk, RAM/VRAM, session limits, network transfer budget, writable persistent storage, and checkpoint compatibility. Fail closed when any condition is missing.
5. **Bounded streaming:** read shards incrementally; do not load the entire corpus into RAM. Deduplicate before splitting. Keep fixed, source-separated validation/test sets to reduce leakage.
6. **Checkpoint protocol:** at step/time intervals save model, optimizer, scheduler, AMP scaler if used, global step, epoch, RNG states, sampler/data cursor, and all relevant hashes. Write to a temporary path, verify, then promote it to the latest checkpoint where supported. Keep a previous known-good checkpoint and verify downloads on restore.
7. **Portable workers:** use a pinned environment definition and provider-specific launch adapters. The same immutable job manifest must work on each approved worker. If hardware/runtime differs, run compatibility checks instead of silently changing settings.
8. **Sequential continuation:** when a session ends, stop cleanly, upload and verify the latest checkpoint, release resources, and wait for the next permitted session. The next worker resumes from the durable checkpoint. Never assume a provider is always available.
9. **Evaluation and promotion:** log loss, token count, throughput, memory, elapsed compute, provider, checkpoint hashes, and validation metrics. Require review before promoting or publishing weights.

## Storage budget

Do not treat 100 GB across clouds as one guaranteed quota. Calculate a budget after checking real account allocations. Include raw approved corpus, normalized/sharded corpus, validation/test split, temporary download/extraction space, checkpoints (model plus optimizer can be several times the weight size), logs, a prior checkpoint, duplicate copies, and network egress.

The 30 GB raw dataset may occupy substantially more or less after normalization/compression; checkpoints and temporary space add overhead. Measure actual bytes with a small approved pilot before uploading the full corpus. For the older PC's 40 GB free disk, do not store the whole corpus there; use it for checks, a small cache, or evaluation after hardware health checks.

## Rollout gates

### Phase 0 — provider and rights inventory
- Confirm data licences, privacy/PII handling, attribution, redistribution constraints, and permission to train.
- Keep `data/mkaos/source-register.json` blocked while `current_approved_sources` is empty or `model_training_allowed` is false.
- Record each provider's actual quota, runtime limits, persistence, egress, terms, and data-retention settings. Use only supported account usage.

### Phase 1 — synthetic end-to-end test
- Build manifest/shard tools using synthetic non-sensitive text.
- Test checksums, interrupted downloads, duplicate shards, and missing storage.
- Stop a tiny training run, restart it on another compatible worker, and prove optimizer/scheduler/RNG/data-cursor restoration.
- Compare resumed and uninterrupted tiny runs within a documented numeric tolerance.
- Confirm a changed config/data/tokenizer hash blocks resume.

### Phase 2 — small approved pilot
- Use a small rights-cleared dataset, not the entire 30 GB corpus.
- Measure transfer time, tokens/second, memory, checkpoint size, restore time, validation loss and session usage.
- Test one provider at a time and confirm checkpoint portability before adding another provider.

### Phase 3 — staged expansion
- Add providers only after their terms and adapters are verified.
- Expand shard volume gradually, verify every shard, and monitor the aggregate byte budget.
- Use the full dataset only after data quality, deduplication, validation split, storage, and compute estimates are documented.

## Explicit non-goals
- No quota evasion, fake accounts, hidden background workers, or attempts to keep a free session alive beyond provider limits.
- No claim that a provider gives permanent free storage/compute.
- No automatic training until approval gates and resume acceptance tests pass.
- No claim that more stored GB alone improves model quality or that 30 GB implies a billion-parameter model.

## Acceptance checklist
- [ ] Provider inventory includes official terms and observed account quota for every selected service.
- [ ] Per-shard hashes, manifest integrity, resumable transfers and missing-shard behavior are tested.
- [ ] Corpus is streamed within a memory cap on a synthetic corpus larger than available RAM.
- [ ] Checkpoint restores model, optimizer, scheduler, scaler, RNG, sampler/data cursor, and step.
- [ ] A worker interruption followed by a different compatible worker resumes successfully.
- [ ] Full disk, quota exhaustion, failed upload, invalid hashes, and unapproved sources fail safely.
- [ ] Data approval remains blocked until source-specific evidence is reviewed.
