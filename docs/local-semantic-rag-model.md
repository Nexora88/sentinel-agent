# MKAOS local semantic RAG model

## Selected model

MKAOS's recommended multilingual embedding model is **BAAI/bge-m3** (MIT license). It supports 100+ languages, dense/sparse/multi-vector retrieval, and up to 8,192 input tokens. The upstream model is about 4.6 GB, so it is a quality-first option rather than a lightweight default for low-memory machines.

Upstream: https://huggingface.co/BAAI/bge-m3

This is an **embedding/retrieval model**, not the MKAOS conversational language model. Provisioning it does not train or install a chat model.

## Explicit provisioning

Model weights are intentionally not committed to Git. Download them only when an operator explicitly provisions the machine:

```bash
python -m pip install -r scripts/rag-model-requirements.txt
python scripts/provision_rag_model.py --model-dir var/models/bge-m3
```

The script resolves the configured upstream revision to a full commit SHA, downloads that exact snapshot, runs a local Turkish/multilingual embedding smoke test (1024 dimensions), and writes `.mkaos-model-sha256.json` from the files actually downloaded. The inventory is generated only after the smoke test succeeds. It does not contain invented or placeholder hashes.

After transfer or before starting a deployment, verify offline:

```bash
python scripts/provision_rag_model.py --model-dir var/models/bge-m3 --verify
```

Verification is offline and fails closed if a file is missing, added, or changed. It never repairs files by downloading them.

## Operational requirements

- Reserve at least 6 GB of free disk space for the model and temporary overhead.
- Use a trusted connection for the one-time provision step; then run inference offline.
- Keep model files and generated inventory outside Git and container build contexts unless the deployment intentionally packages them.
- Runtime code must load the **local path** with remote downloads disabled; it must not silently fall back to a Hugging Face model ID.
- Treat the generated hash inventory as deployment evidence, not proof that retrieval quality is good. Run the repository's Turkish retrieval evaluation against a labelled dataset before claiming quality improvements.
- The provisioning script does not alter the MKAOS chat model and does not claim chat-model training.
