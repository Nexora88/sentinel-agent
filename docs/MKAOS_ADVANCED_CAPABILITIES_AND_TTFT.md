# MKAOS advanced capabilities and TTFT acceptance

This document records what is implemented, what remains experimental, and the order required before a target-device TTFT result is publishable.

## Advanced capability status

| Capability | Repository evidence | Not yet proven |
|---|---|---|
| Encrypted Crypto-RAG | Opt-in AES-256-GCM SQLite backend integrated with RAG; explicit key and separate path required | Production key management, restore drill, migration approval, and storage/WAL retention |
| Browser isolation | Separate non-root Playwright screenshot worker and local fixture | Immutable image digest, full SSRF/DNS-rebinding/resource-exhaustion review, and any live-site workflow |
| Zero-trust agent mesh | Signed task envelopes and TLS 1.3+ context / peer identity helpers | Live listener, WireGuard peer provisioning, CA operations, revocation distribution, and deployed network tests |
| Rust local inference | Multi-layer GQA decoder, KV cache, SafeTensors loader; pinned tokenizer and real-weight logits checks passed in CI for tested cases | General Turkish answer quality, full context behavior, accelerator support, and target-device performance |
| Developer ecosystem | PR #123 merged; CLI/MCP package build and tests plus portability matrix passed | Actual Cursor/Claude Code desktop-client interoperability and PyPI publication |

These are implementation states, not a claim that all capabilities are enabled or production-deployed. Keep opt-in modules disabled until their operator-controlled acceptance gates pass.

## Model artifact readiness

The pinned SmolLM2-135M-Instruct revision and measured SHA-256 values are recorded in \`models/smollm2-135m-instruct/model-lock.json\`. The weights and tokenizer binaries are not committed to this checkout. The CI parity result is bounded to the tested tokenizer/chat-template and real-weight logits cases; it is not a Turkish quality or device-speed result.

Before local inference:
1. Retrieve only the pinned SafeTensors and JSON/text artifacts on a machine with sufficient disk and memory.
2. Verify every downloaded file against the committed lock.
3. Run \`tools/validate_tokenizer.py\` and \`tools/validate_model_logits.py\` against the pinned artifacts.
4. Run the held-out Turkish evaluation and record human-reviewed factuality, instruction following, robustness, and refusal scores.
5. Measure memory and stable generation throughput before TTFT.

## TTFT definition and current instrumentation

\`mkaos_generate\` emits \`model_load_ms\`, \`prefill_ms\`, \`first_token_ms\`, and \`inference_total_ms\`. \`first_token_ms\` starts immediately before prompt prefill and stops when the first token is sampled. Model loading is reported separately.

This is local inference first-token latency. It is **not** client-visible streaming TTFT: the current CLI prints a completed JSON result after generation rather than delivering token events to a connected client. Do not label it as streaming TTFT or include network/client buffering in claims.

## Target-device measurement protocol

After artifact, correctness, held-out quality, memory, and throughput gates pass:

- Record device model, CPU, RAM, GPU/VRAM if available, OS, power mode, Rust toolchain, release flags, commit SHA, model revision, model/tokenizer SHA-256, and prompt-set version.
- Keep the same physical device, prompt, model files, generation limit, and build profile for every comparison.
- Separate process/model cold-start from in-process first-token latency and prompt prefill.
- Use one warm-up, then at least 5 measured repetitions; report median and p95, not only the best run.
- Record generated token count, total generation time, tokens/second, peak RSS, failures, and raw non-sensitive outputs.
- Run offline verification separately; an environment variable alone is not proof of network isolation.
- Preserve the JSON report and review Turkish outputs manually. Do not compare unlike model revisions, quantization, or hardware as if equivalent.

## Current target-device blocker

The audited Windows checkout contains the model lock and documentation only; it does not contain \`model.safetensors\`, \`config.json\`, or tokenizer files. No local Ollama command was found during this audit. Therefore no local model load, generation, or TTFT result was collected. Do not download large artifacts or start a heavy compile until available disk/RAM has been checked and the user has approved the resource use.

## Release rule

TTFT is the final performance gate, not the first. If any artifact, correctness, quality, memory, or repeatability gate is missing, report TTFT as **not measured** and keep the local Rust engine experimental.