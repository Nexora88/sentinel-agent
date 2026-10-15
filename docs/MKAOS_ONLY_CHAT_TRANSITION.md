# MKAOS-only chat transition

## Enforced behavior

- All chat, coding, planning, and agent generation requests go to the resident Rust MKAOS endpoint configured by `MKAOS_BASE_URL`.
- The legacy `MKAOS_ENABLED=false` setting no longer changes the provider. It is intentionally ignored, so there is no Ollama chat rollback path.
- MKAOS connection errors remain visible. The client does not retry the prompt against another chat model.
- Docker Compose starts MKAOS by default instead of requiring the `mkaos` profile.
- The Ollama container is temporarily retained **only for Chroma/RAG embeddings**. This is not yet full runtime independence. Native MKAOS embeddings must be implemented and validated against retrieval-quality fixtures before the Ollama image, model volume, `langchain-ollama` dependency, and legacy embedding adapter can be deleted safely.
- The resident MKAOS model weights are still third-party SmolLM2-135M-Instruct. An independent inference engine does not mean independently trained weights.

## Required next gates before removing the final Ollama dependency

1. Implement a versioned native embedding interface in Rust, with deterministic output and dimension/normalization tests.
2. Evaluate retrieval recall@k and ranking against a fixed, locally stored multilingual/Turkish corpus; include existing Chroma migration compatibility.
3. Replace `OllamaEmbeddings` with a native MKAOS embedding adapter and add no-network integration tests.
4. Remove Ollama image/model volume, all Ollama environment variables and `langchain-ollama` from runtime requirements only after those tests pass.
5. Re-run full Python/Rust CI, network-egress tests, RAG persistence/migration tests, and target-device quality/stability/memory measurements.
6. Keep the dedicated TTFT test deferred until the other gates and target-device checks pass.

## Start locally

Fetch the pinned model before starting the isolated Compose network:

```bash
python tools/fetch_model.py --output-dir models/smollm2-135m-instruct
docker compose up --build -d
docker compose exec sentinel python -c "import urllib.request; print(urllib.request.urlopen('http://mkaos:11435/health').read().decode())"
```

The first run also requires the temporary embedding model to be present in the local Ollama volume. Do not interpret CI smoke tests as proof of strong Turkish semantic quality or performance on the target device.
