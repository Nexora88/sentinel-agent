# MKAOS same-device cold/warm benchmark

Use `tools/benchmark_mkaos_device.py` on the physical machine that will run MKAOS. The script launches a fresh server for each cold trial, then starts one resident server for warm requests. It writes raw outputs, latency samples, sampled RSS/available NVIDIA VRAM, artifact hashes, selected model configuration fields (including parameter count when present), hardware details and the Git revision into a JSON report. VRAM is sampled system-wide and may include other GPU workloads; a missing sample is reported as unavailable, never as zero.

## Example

```bash
python tools/benchmark_mkaos_device.py \
  --server-command "./engine/mkaos-hf-adapter/target/release/mkaos_server artifacts/smollm2-135m-instruct 127.0.0.1:11435" \
  --health-url http://127.0.0.1:11435/health \
  --generate-url http://127.0.0.1:11435/api/generate \
  --model-manifest artifacts/smollm2-135m-instruct/model-lock.generated.json \
  --runs 5 --warm-runs 20 --max-new-tokens 48 \
  --network-isolation not-verified \
  --output artifacts/mkaos-device-benchmark.json
```

Use the exact same physical device, power profile, model/tokenizer hashes, prompt set, generation limit, Rust toolchain and release flags when comparing revisions. Preserve the JSON artifact and human-review the output texts. Never label a result as offline just because `HF_HUB_OFFLINE=1` is set; the process or container must actually be denied network egress. In Docker, enforce that with `--network none` and separately test that local model loading still succeeds.

The script deliberately does not report TTFT from whole-response latency. TTFT needs token-stream timestamps and should be measured only after tokenizer/checkpoint correctness, stable generation throughput, memory behavior and held-out quality have been checked.

The included prompts are a reproducible smoke set, not a statistically representative Turkish quality benchmark. Keep the separate held-out quality set untouched and use human review for factuality and instruction-following.
