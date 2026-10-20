# MKAOS local semantic RAG setup

MKAOS uses a **local semantic embedding model by default** for retrieval. It does not download weights at application startup, and it does not silently fall back to an external service. If the model or its file inventory is missing or mismatched, semantic RAG fails closed with a configuration error.

## Model choice

Use a reviewed, locally installed multilingual Sentence Transformers model, with this default directory name:

`models/embeddings/paraphrase-multilingual-MiniLM-L12-v2/`

This model family supports multilingual similarity, including Turkish. It is a retrieval encoder, not the MKAOS chat-generation model. The repository does not bundle model weights. Before use, review the exact publisher, immutable revision, license/notice, privacy implications, and file inventory. Do not assume a model is approved solely because it is hosted on a public model hub.

## Prepare before offline launch

1. On a trusted staging machine with authorized network access, obtain the selected model from its official publisher and pin an immutable revision. Do not download it during application startup.
2. Copy the complete model directory to `models/embeddings/paraphrase-multilingual-MiniLM-L12-v2/`.
3. Install the repository's Python requirements when building the image; `Dockerfile` includes `requirements-semantic.txt` in the build stage. The runtime container does not run `pip install`.
4. Create a file inventory outside the model directory:

   ```bash
   python tools/hash_local_embedding_model.py \
     --model-dir models/embeddings/paraphrase-multilingual-MiniLM-L12-v2 \
     --output models/embeddings/embedding-manifest.json
   ```

5. Verify the inventory before deployment:

   ```bash
   python tools/hash_local_embedding_model.py \
     --model-dir models/embeddings/paraphrase-multilingual-MiniLM-L12-v2 \
     --verify models/embeddings/embedding-manifest.json
   ```

6. Ensure the host `models/` directory is mounted read-only at `/app/models` in Compose. The default container paths are:
   - `SEKA_EMBEDDINGS_PROVIDER=local-semantic`
   - `SEKA_REQUIRE_SEMANTIC_EMBEDDINGS=true`
   - `SEKA_LOCAL_EMBEDDING_MODEL_PATH=/app/models/embeddings/paraphrase-multilingual-MiniLM-L12-v2`
   - `SEKA_LOCAL_EMBEDDING_MANIFEST=/app/models/embeddings/embedding-manifest.json`

7. Start with `docker compose up --build` only after the model directory and manifest exist. The `seka_isolated` network limits container egress, but host firewall rules and image/model supply-chain review are still required for a strong offline claim.

## Validation gates

- Test Turkish paraphrase retrieval, inflectional variants, code identifiers, exact symbol lookup, and negative/unrelated queries.
- Compare Recall@k, MRR/nDCG, latency, memory use, and retrieval failure cases against the native n-gram baseline on a frozen, human-reviewed set.
- Do not claim semantic quality based only on successful model loading.
- Rebuild the inventory after any model-file change. A matching SHA-256 inventory proves file identity, not licensing, privacy approval, or model quality.
- Embedding providers use separate Chroma collection suffixes; changing providers does not make old vectors compatible. Re-ingest documents when switching embedding spaces.
- For an explicitly approved legacy experiment only, `SEKA_EMBEDDINGS_PROVIDER=ollama` may be selected with the `legacy-ollama-embeddings` Compose profile. The default remains local semantic retrieval.
