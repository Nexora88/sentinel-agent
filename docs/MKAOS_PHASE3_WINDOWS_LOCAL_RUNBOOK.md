# MKAOS Phase 3 — Windows local inference and evaluation runbook

## Target machine

- Windows PC, Intel Core i5 (generation/model not yet recorded)
- 8 GB RAM
- At least 200 GB free disk
- GPU not assumed; first milestone is CPU-only

This is a plan, not evidence that the target PC has been tested. Record exact CPU model, Windows version, architecture, free disk, and GPU before selecting final runtime settings.

## Independence contract

1. The default chat path must remain the repository's native MKAOS runtime. Do not make a third-party API, hosted inference endpoint, Ollama server, or remote fallback a requirement.
2. Ollama or another local model runner may be used only as an explicitly selected comparison/baseline. A local runner is not the same thing as the MKAOS-native checkpoint format, and a model file must not be assumed compatible with `mkaos-generate`.
3. No model weights, corpus, or checkpoints are downloaded automatically by the application. Any manually obtained weights need source, license, version, and SHA-256 recorded before use.
4. Offline/sovereign status must not be reported as proven merely because an endpoint is localhost. Verify outbound blocking at the OS/firewall layer and test attempted egress.

## Phase 3 sequence

### A. Read-only machine inventory (PowerShell)

Run locally on the target PC:

```powershell
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$gpu = Get-CimInstance Win32_VideoController

[pscustomobject]@{
  Windows = $os.Caption
  Version = $os.Version
  Architecture = $os.OSArchitecture
  RAM_GB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
  CPU = $cpu.Name
  Cores = $cpu.NumberOfCores
  LogicalProcessors = $cpu.NumberOfLogicalProcessors
  FreeC_GB = [math]::Round($disk.FreeSpace / 1GB, 2)
  GPU = ($gpu.Name -join "; ")
} | Format-List
rustc --version
cargo --version
```

Missing Rust tools are an inventory result, not a reason to silently switch to a cloud runtime.

### B. Baseline and build

1. Check out the branch/revision under review and inspect `engine/mkaos-inference/`, `core/mkaos_native_chat.py`, `core/runtime_profile.py`, and the existing tests before running anything.
2. Build and run the native engine using the repository's documented commands. Do not assume a Linux path such as `/usr/local/bin/mkaos-generate` exists on Windows; configure the explicit generator path to the verified Windows binary if the adapter supports it. If Windows compilation is not supported, record the blocker and add/test Windows support before claiming this PC runs the native engine.
3. Start with CPU-only settings, short context, and a small batch. Watch process memory and response latency. Do not begin fine-tuning on an 8 GB machine until measured memory use and checkpoint size show sufficient headroom.
4. Use a tiny, explicitly licensed test fixture for the first smoke test; it is not training approval.

### C. Evaluation before any training

Record a baseline report containing:
- exact source revision and binary hash;
- checkpoint path, SHA-256, byte size, provenance, and license;
- hardware/OS details;
- Turkish prompt set version and expected-answer rubric;
- pass rate for instruction following, Turkish fluency, factuality, refusal/safety behavior, and context handling;
- latency, peak RAM, crashes, and timeouts;
- network-egress test results.

Keep the test set separate from any later training examples. Do not present a successful process start or synthetic CI training as proof of Turkish language quality.

### D. Privacy and sovereignty tests

- Run with network access blocked by a Windows Firewall rule or an isolated network, according to the operator's policy.
- Capture/inspect attempted outbound connections while testing chat, retrieval, logs, and errors. A localhost URL alone is not proof of isolation.
- Verify that prompts, outputs, uploaded files, and corpus content are not transmitted or written to unexpected locations.
- Verify clean failure when the model/checkpoint is missing, the hash mismatches, or generation times out. No silent remote fallback.
- Record evidence and repeat after changes to runtime, dependencies, or model configuration.

## Training and source approval gate — MUST REMAIN CLOSED

Until documented review is complete, retain:
- `current_approved_sources = []`
- `corpus_ready = false`
- `model_training_allowed = false`

For every proposed source, preserve its exact revision/URL, acquisition date, license and redistribution terms, privacy/content review, attribution requirements, and a SHA-256 manifest. Review sample records before approving the complete source. Weight redistribution has a separate approval gate. Do not launch real training merely because disk space is available or a download/checksum step succeeded.

## Exit criteria

Phase 3 is complete only when the native engine runs on the target Windows machine without remote inference, a reproducible baseline evaluation is saved, egress/privacy checks pass with evidence, and all model/checkpoint provenance is recorded. Training remains disabled until the independent source-approval gate is satisfied.


## Base-model decision — avoid a false compatibility promise

The first integration target is the smallest real checkpoint already validated against the repository's Rust engine, not an arbitrary model converted by renaming its file. The repository's independence milestone records a pinned SmolLM2-135M reference-parity smoke test; confirm the current lock file, measured hashes, tokenizer/template, and exact tested revision before reusing it. This is a bring-up baseline, not a claim of strong Turkish assistant quality.

Do not label Qwen2.5-Coder-1.5B or Llama-3.2-1B as drop-in MKAOSW models. Model-format conversion alone does not translate architecture or tokenizer. The current native engine uses the MKAOS byte-tokenizer/decoder contract; a different base model requires an explicit architecture and tokenizer implementation, a converter, reference-logit/token-ID parity tests, and end-to-end tests before it can be selected. If the immediate goal is a useful answer on the target PC, compare a separately installed local runner only as a temporary, opt-in baseline; it must not become a hosted API or hidden default dependency.

### Honest performance and hardware target

- Do not promise 1,700 tokens/second. No target-PC measurement currently supports that number; CPU generation speed depends on the exact processor, model, quantization, context, and implementation.
- The first acceptance target is successful local generation, correct tokenizer/checkpoint loading, no network inference, bounded RAM, and a reproducible Turkish evaluation report—not a marketing speed claim.
- On 8 GB RAM, begin with a small inference checkpoint and short context. Fine-tuning a 1B–1.5B model on CPU may be impractically slow and memory-constrained; 200 GB disk space does not provide compute or RAM. Do not promise “a few days” without a measured pilot.
- A 474,498-document count is not sufficient evidence that the corpus is clean or legally usable. Require the exact corpus manifest, SHA-256s, source/revision, license and redistribution terms, privacy/content review, attribution requirements, and human-reviewed samples. Military/cybersecurity material must be assessed source-by-source; do not assume public availability grants training rights.

### Staged implementation

1. **Boot without 503:** verify the already-supported real checkpoint path and Windows executable path. Add a smoke test that distinguishes missing configuration from a genuinely successful local response. Never silently fall back to a remote service.
2. **Prove the base:** run tokenizer parity, checkpoint hash/shape validation, deterministic generation, RAM/latency/token-per-second measurements, and a held-out Turkish prompt suite. Publish measured results with hardware and revision.
3. **Expand model compatibility only with evidence:** choose one candidate, implement its actual architecture/tokenizer, and require reference parity before converting it to MKAOSW. Keep model license and redistribution review separate from code compatibility.
4. **Fine-tune only after approvals:** first run a tiny LoRA/adapter feasibility pilot on a rights-cleared, deduplicated subset and measure peak RAM, time per step, and validation quality. The 474,498-document corpus remains blocked until its source and contents are approved. Keep current_approved_sources empty, corpus_ready false, and model_training_allowed false until that evidence exists.
5. **Keep safety outside model weights:** use core/reasoning_engine.py for bounded draft/critique/synthesis and deterministic local policy checks for enforceable rules. Treat model outputs as untrusted; test prompt injection, false claims, refusal behavior, and filter bypasses. A reasoning prompt is not a security boundary, and symbolic filters cannot guarantee removal of all bias or manipulation.

**Independence principle:** using an openly licensed pretrained model locally is a practical starting point, not surrendering operational independence. MKAOS still owns the runtime integration, policy enforcement, evaluation, data approvals, and deployment. The long-term fully native path remains viable, but model compatibility and measured performance must be earned by tests—not assumed.
