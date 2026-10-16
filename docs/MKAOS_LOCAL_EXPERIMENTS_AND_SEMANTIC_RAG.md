# MKAOS local experimentation and semantic RAG

## Owner-authorized local-only training

The normal training path still requires the source register to approve each exact source release and model-weight distribution. For development iteration only, the trainer now exposes a separate opt-in flag:

```bash
python tools/train_mkaos_from_scratch.py \
  --corpus /path/to/local-corpus.jsonl \
  --manifest /path/to/local-manifest.json \
  --output-dir /path/to/private-mkaos-output \
  --experimental-local-only
```

This mode is accepted only when the manifest contains:

- `data_rights_mode: "owner_supplied_local_nonredistributable"`
- `source_kind: "owner_created_or_rights_cleared_local"`
- non-empty `records` with source IDs, sample IDs, exact text SHA-256 hashes, and train/validation/test splits.

The manifest validator and corpus hash checks still run. The explicit flag does not certify that a source is lawful, does not approve third-party datasets, and does not clear personal data. The output report marks the run as experimental and not approved for redistribution. Keep the corpus, manifest, checkpoint, and report local until source rights, privacy, and weight-distribution review are completed. Do not use this mode to re-label Common Voice, Wikipedia, Tatoeba, HPLT, or another third-party corpus as owner-created.

## Local semantic retrieval (optional)

The default `mkaos-native` embedding is a deterministic word/character n-gram hashing baseline. It is useful for offline lexical retrieval but is not a trained semantic model.

To use a trained embedding model that is already present on disk:

1. Install the optional adapter dependency: `pip install -r requirements-semantic.txt`.
2. Place a compatible Sentence-Transformers model in a local directory using a separately reviewed, permitted acquisition process.
3. Set `SEKA_EMBEDDINGS_PROVIDER=local-semantic`.
4. Set `SEKA_LOCAL_EMBEDDING_MODEL_PATH=/absolute/path/to/local/model`.
5. Start the application with network access disabled for the embedding model process and evaluate retrieval against a held-out Turkish query/document set.

The adapter requires an existing local directory, uses `local_files_only=True`, and sets `trust_remote_code=False`. It does not download weights. The semantic provider has a separate Chroma collection suffix so vectors from different embedding spaces are not mixed. Switching providers does not migrate or re-embed old records; re-ingest the source documents into the new collection.

This is an optional retrieval improvement, not proof that MKAOS's generative model has learned Turkish. For full independence, the project still needs to train and evaluate its own embedding model, publish a reproducible Turkish retrieval benchmark, and report recall@k / MRR or nDCG against a held-out dataset. Do not describe the current hash baseline or an external embedding model as MKAOS-owned learned weights.
