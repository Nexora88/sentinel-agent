# Crypto-RAG migration — non-destructive procedure

The current core/rag.py uses a persistent Chroma collection. core/crypto_rag.py is a
separate encrypted store; it does not silently replace Chroma. The migration tool
copies records into a new AES-256-GCM SQLite store and leaves the source untouched.

## Before running

- Schedule a maintenance window and stop every process that can write to the Chroma
  directory. Confirm that the app and background jobs are stopped.
- Keep the Chroma directory on a local filesystem and choose a new backup directory
  and a new destination path. Neither path may already exist or be inside the source.
- Generate a 32-byte key locally with:
    python -c "from core.crypto_rag import generate_key; print(generate_key())"
  Store it in a password manager or operating-system secret store, not in the database,
  source control, shell history, or logs. Export its Base64 value as
  MKAOS_CRYPTO_RAG_KEY only in the local migration process environment.
- Identify the exact existing collection name. MemoryStore.storage_collection_name
  includes the embedding-provider suffix; do not guess it.

## Run and verify

Example paths are placeholders; substitute the actual local paths and exact collection:

    export MKAOS_CRYPTO_RAG_KEY='BASE64_KEY_STORED_OUTSIDE_THE_DATABASE'
    python -m tools.migrate_crypto_rag \
      --source-dir ./memory \
      --collection sentinel_memory_native_hash_v1 \
      --backup-dir ./backups/chroma-pre-crypto-rag \
      --destination ./memory/encrypted-vectors.sqlite3 \
      --source-quiesced

The tool refuses to run without --source-quiesced, refuses an existing backup or
destination, hashes the source directory before and after backup, verifies the backup
digest, copies records in bounded batches, decrypts each new record to compare ID,
document, metadata and embedding, and checks the final record counts. It prints a
verification report and does not delete or rewrite source records.

## Acceptance gates

1. backup_verified must be true and a backup digest must be recorded.
2. source_records, destination_records, and verified_records must match.
3. Reopen the encrypted store with the same key and run application-level retrieval tests.
4. Verify restart behavior, backup restore, wrong-key failure, tamper detection, and
   disk-sidecar behavior in a non-production copy.
5. Review privacy, latency, capacity, key recovery, and restore procedures before
   changing the app to use the encrypted store.

A failed or interrupted migration intentionally leaves the plaintext source untouched.
Do not delete the old directory automatically. Removal requires a separately verified
restorable backup, a documented retention decision, and explicit human approval. The
encrypted store also protects only its own payloads; Chroma's existing files, backups,
logs, process memory and keys are not retroactively encrypted.
