# MKAOS: HF portability, output guardrails, PEFT and offline operation

## 1. Hugging Face checkpoint portability (CPU-first)

Run the local, read-only preflight:

```bash
python tools/mkaos_hf_adapter_preflight.py /path/to/local-model --output hf-preflight.json
```

It reads `config.json` and local `.safetensors` headers without importing PyTorch or downloading anything. It reports model architecture, tensor names/shapes, tokenizer-related files, and presence (not approval) of license/model-card files.

**It does not convert weights.** The repository's experimental `MKAOSW1` format and byte tokenizer are not equivalent to Hugging Face model formats/tokenizers. Llama 3.2 and Qwen2.5-Coder weights cannot safely be converted by changing a filename or dumping tensors into one file. A real adapter needs architecture-specific tensor mapping, tokenizer parity, dtype/quantization rules, positional encoding, normalization, KV-head layout, numerical parity tests, and model-specific license review. Until those exist, compatibility must remain explicitly unsupported rather than producing a broken checkpoint.

The preflight does not fetch files, modify source model files, certify model integrity beyond parsing headers, or decide license/redistribution rights. Verify a trusted SHA-256 separately and review the exact model card and license before use.

## 2. Deterministic local output guard

`core/constitutional_guard.py` is a small post-processing primitive for obvious private-key and token-shaped output. It is deterministic and runs on CPU; it does not require a GPU or model call. It is not a general fact checker, does not establish that a historical claim is true, and does not detect all prompt injection, malware, bias, or backdoors. Nationality is not evidence of manipulation. Historical and security-sensitive claims should be checked against named, reliable sources and tests.

Callers should pass the final user-visible answer through `guard_output(text)`. If `findings` is non-empty, log only the finding labels/counts—not the original secret—and tell the user that a possible credential was redacted. Keep credentials out of prompts and logs in the first place.

## 3. PEFT/LoRA training gate

Do not start a training run just because a corpus was downloaded or its hashes match. Before PEFT/LoRA, record:
- exact base model revision and license terms, including fine-tune and redistribution restrictions;
- every dataset source, license/terms, attribution requirements, privacy/PII review, and explicit approval reference;
- deduplication and train/validation/test split hashes, with the test set held out;
- hardware, peak RAM/VRAM, runtime, seed, adapter config, loss curves, and evaluation results.

Wikipedia and CVE advisories are not a blanket license for every downstream use. The repository's existing source-approval gate remains authoritative; this document does not approve the previously collected 474,498-document corpus or any CVE corpus. An 8 GB RAM CPU machine is suitable for metadata checks and small tests, not a promise of practical LoRA training on multi-billion-parameter models.

## 4. Offline and air-gap hardening

The default Compose `seka_isolated` network is configured as an internal Docker network. That constrains containers attached to it; it does **not** disable the host's network card or prove the entire computer is offline.

For stronger isolation:
1. Prepare and hash images/models while online, then shut down the bootstrap/networked profiles.
2. Use the offline Compose overlay and verify the effective configuration with `docker compose -f docker-compose.yml -f docker-compose.offline.yml config`.
3. Apply host-level outbound-deny firewall policy from a local console, allowing only explicitly required loopback/local-LAN traffic. Test on the actual host and check IPv4 and IPv6; do not blindly apply firewall commands over a remote session.
4. Capture/inspect outbound connection attempts during a test run and repeat after upgrades. Disable integrations and remove credentials that are not needed.
5. Verify that failure to reach a remote service fails closed; no silent hosted-model fallback.

A firewall rule or Docker network declaration is not proof by itself. Host services, DNS, update agents, other containers, mounted sockets, and physical access remain outside this app-level guarantee. Report results as tested scope, date, host OS, and commands—not as “unbreakable” security.
