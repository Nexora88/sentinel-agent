# MKAOS production validation gates — 16 October 2026

This is a release evidence checklist, not a claim that the system is production-ready. A green CI job alone does not establish data-license compatibility, Turkish-language quality, distributed-training correctness, or production security.

## Current decision

- **1B / 1.5B training:** Not run. The profile JSON files are planning inputs, not trained models.
- **Corpus:** The Turkish Wikipedia 20260901 download/preparation pipeline exists. Source rights, privacy, attribution/ShareAlike compatibility, and model-weight distribution remain pending human review. A preparation report is not an approval.
- **Training hardware:** Real GPU/RAM/disk measurements and small-pilot results for the 1B profile are not recorded. Do not start large training if resources are insufficient.
- **PostgreSQL:** An encrypted storage adapter and SQL RLS schema exist. A new CI job tests real PostgreSQL 16 using a non-superuser application role, tenant isolation, and encrypted round trips. These tests do not prove that the application uses this adapter by default, that backups restore correctly, or that multi-replica production behavior is validated.
- **Semantic encoder:** The Rust side has a vector contract and ranking primitive; there is no trained MKAOS-owned tokenizer-plus-encoder model. The n-gram fallback must not be reported as a semantic encoder.

## Evidence required before release

### A. Corpus and source rights — human action required

1. Record exact release, official license URL, SHA-256 of acquired files, and data-use terms for every source.
2. A human reviewer must inspect the deterministic sample queue and separately record language quality, personal/sensitive data, attribution, and document-level split leakage.
3. Training use, commercial use, raw-data redistribution, and model-weight distribution are separate decisions.
4. Source approvals must be recorded in data/mkaos/source-register.json and the training manifest must pass the governance validator before normal training. Wikipedia, Common Voice, Tatoeba, and HPLT are never auto-approved.
5. Archive the workflow report artifact; full corpus retention stays disabled by default.

### B. Model training — suitable hardware and measurements required

1. Validate training, epoch checkpointing, resume behavior, loss curves, and independent-test reporting on a small approved pilot.
2. Measure single-GPU and DDP separately; prove equal batch counts per rank, restoration of optimizer/scaler/RNG state, and interruption recovery.
3. Do not start the 1.5B run before recording peak GPU memory, RAM, disk, and duration for the 1B profile.
4. Independent-test loss is only one metric. Turkish human evaluation, task-based tests, and regression tests are required.
5. Record checkpoint, tokenizer, manifest, and training-report SHA-256 values together. Until a real run exists, do not say the model was trained.

### C. PostgreSQL persistence — automated tests plus operational review

1. The mkaos-postgres-integration CI job must pass. The application role must not have SUPERUSER or BYPASSRLS; cross-tenant reads/writes must be blocked; ciphertext must not contain plaintext payloads.
2. The production tenant identity must be derived from authenticated identity, not directly from an untrusted request body.
3. Document key management and rotation, connection pooling, migration/rollback, encrypted backups, and a real restore drill.
4. Integrate the adapter with the existing memory path explicitly, behind a feature flag, and test canary rollout and rollback. CI does not equal application integration.

### D. Semantic retrieval — model and measurements required

1. Pin the encoder model, tokenizer, version, license, and hash manifest. Default behavior must not silently download models or switch to a third-party model.
2. Measure Recall@k, MRR, and nDCG on Turkish query-document pairs against the n-gram baseline; keep the evaluation set independent.
3. Test model-space/version mismatch, empty or NaN vectors, corrupted checkpoints, and offline behavior.
4. If the encoder does not load, the UI/report must not claim semantic mode is active; it must name the actual fallback.

## Suggested verification commands

    python -m unittest tests.test_postgres_memory_store -v
    python -m unittest discover -s tests/integration -p "test_postgres_memory_store_integration.py" -v
    python tools/plan_mkaos_training_scale.py configs/mkaos/train-1b.json
    python tools/plan_mkaos_training_scale.py configs/mkaos/train-1_5b.json

The integration test requires MKAOS_TEST_POSTGRES_DSN and a temporary test encryption key, and must run only against a disposable test database. These checks are not a substitute for a real 1B/1.5B training run.

## Stop conditions

Do not start full training until rights-reviewed sources and sufficient hardware evidence exist. Do not make PostgreSQL the production default until RLS, key-management, and restore checks are complete. Do not publish a semantic-search claim until an encoder has been trained or otherwise approved, measured, and integrated.
