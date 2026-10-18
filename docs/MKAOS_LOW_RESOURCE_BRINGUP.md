# MKAOS: low-resource local bring-up

MKAOS should prove one useful local workflow before adding more features. This guide is deliberately CPU-first and avoids exhausting an 8 GB PC.

## 1. Inspect before running anything

From the repository root, run:

```powershell
python tools/mkaos_local_preflight.py
```

The report is JSON and read-only. It checks free disk space, available RAM where supported, Rust/Cargo availability, and any explicitly configured local generator/checkpoint. It does **not** download a model, start inference, send network requests, alter source approval, or enable training.

Optional threshold:

```powershell
python tools/mkaos_local_preflight.py --min-free-gb 8
```

A missing checkpoint is a useful finding, not a reason to download weights automatically. If a checkpoint is configured, the script verifies its SHA-256 only when a valid `MKAOS_NATIVE_SHA256` is provided.

## 2. Keep the first run small

- Start with CPU-only execution and a short prompt/context.
- Do not start training or fine-tuning on an 8 GB machine as the first test.
- Record the exact commit, checkpoint provenance/license/hash, response latency, peak process RAM, and output quality separately.
- Test with network egress blocked at the operating-system/firewall layer. This preflight itself does not test network isolation.
- If the native checkpoint or generator is absent, report that blocker explicitly. Do not silently use a remote API.

## 3. What success means (and does not mean)

A successful preflight means only that local setup information was collected. It does not prove that the native engine generates useful Turkish, that a model fits in RAM, that a checkpoint is architecture-compatible, or that the machine is air-gapped.

The model/data training gate remains closed until source rights, license, privacy, attribution, and redistribution review are documented. Downloading a dataset or passing a checksum is not approval.

## Product focus

For public demos, prioritize one verifiable capability over a long feature list: local inference with a recorded benchmark, a visible source/hash report, and a repeatable privacy test. Publish measured results—including failures—instead of claiming unsupported speed, sovereignty, or language quality.
