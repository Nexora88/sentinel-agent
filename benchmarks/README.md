# MKAOS benchmark protocol

This protocol is defined before collecting measurements so MKAOS and Ollama can be compared fairly.

## Fixed conditions

- Use the same physical machine, OS session, power mode, prompt JSON, model revision and quantization where possible.
- Record CPU/GPU model, RAM, OS/kernel, Rust version, build profile, model SHA-256, tokenizer SHA-256, runtime version, warm/cold cache state, and random seed.
- Do not compare a quantized model in one runtime with full-precision weights in the other without labeling that difference.
- Run each prompt at least 5 times after one warm-up; report median and p95, not only the fastest run.
- Use a fixed generation limit and stop-token configuration. Save outputs for human review.

## Metrics

Each run must capture:
- prompt id and model/artifact hashes
- exact output text and generated token count
- first-token latency in milliseconds
- total latency in milliseconds
- generated tokens per second (excluding prompt tokens)
- peak resident memory (RSS) in MiB
- task-level checks and human-reviewed correctness
- runtime errors, invalid outputs, EOS/stop behavior

Automated substring checks are smoke tests, not a substitute for semantic evaluation. Report Turkish and English separately. Never claim a winner if the model/tokenizer/precision/hardware conditions differ.

## Current status

The prompt set exists, but there are no benchmark measurements yet because the Rust runtime cannot currently load the selected pretrained model. Ollama remains enabled as the fallback. Do not fill results with estimates or synthetic numbers.
