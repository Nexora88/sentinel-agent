# MKAOS User-Ready and Multimodal Release Plan

Status: implementation plan and acceptance contract; not evidence that a model has been trained, independently evaluated, or released.

## 1. Product architecture: strongest models, honest boundaries

MKAOS should be Turkish-first and local-first, with a capability-based model registry rather than hard-coded provider model names. Model names, availability, license, costs, context limits, modalities and API versions change. Verify exact IDs against official provider documentation at release time and record the verification date.

Every model entry must declare provider and exact version ID; text/image/audio/video/tool capabilities; local or remote execution; data residency and whether prompts/files leave the device; license and retention/training policy; rate/cost limits; tested hardware/runtime; quantization and tokenizer compatibility; and SHA-256/provenance for local artifacts.

Routing policy:
1. Local/private mode is the default. It must make no outbound model requests. If no verified local model is installed, explain that clearly; never silently upload content.
2. Advanced cloud providers are opt-in. Show provider/model, data that will be sent and potential cost before first use. Allow revocation and a session-level local-only lock.
3. Route only to models whose declared capabilities match the task. Image, audio and video support must be tested independently.
4. Never silently switch providers, upload files, or retry without limits. Show clear Turkish errors.
5. Treat every model upgrade as a new immutable version with manifest and hashes; never overwrite the known-good model.

Do not claim “latest” just because a name is in configuration. Check official release documentation at release time.

## 2. Reproducible training

### Data admission
- Use only sources whose license and intended use have been reviewed.
- Record source URL, publisher, license/version, retrieval date, terms snapshot, dataset version, archive SHA-256, preprocessing revision, exclusions and redistribution/weight-training permission.
- Exclude personal/sensitive data, secrets, unapproved copyrighted material and unreviewed sources.
- Deduplicate and split train/validation/test by source or document before chunking to reduce leakage.
- Require two human sign-offs for data rights and privacy. A source marked permitted_use_now=false remains blocked.

### Fixed training manifest
Persist architecture, parameter count, tokenizer revision/hash, dataset manifest/hash, train/validation/test IDs, seed, optimizer, learning rate/schedule, batch and accumulation sizes, context length, precision, gradient clipping, epoch/step limit, software/runtime versions, hardware details, start/end time and exit status. Save the exact command and environment lockfile.

### Required artifacts
Checkpoint and SHA-256; tokenizer and SHA-256; model/tokenizer compatibility manifest; training log and metrics; source/data manifest; evaluation outputs; software versions; and a model card with intended use, limitations and known failure modes. A successful process exit alone is not a quality result. Stop if data approval, compute preflight or artifact verification fails.

## 3. Checkpoint integrity and offline inference

Before loading a checkpoint:
1. Parse the manifest and reject unknown formats.
2. Verify SHA-256 for every required artifact before deserialization.
3. Verify architecture, tokenizer ID/hash, vocabulary and special-token contract.
4. Reject missing files, hash mismatch, incompatible versions and unexpected network access with actionable errors.
5. Run in a clean environment with outbound networking disabled and capture process/network evidence.
6. Run Turkish smoke prompts and deterministic regression tests; save stdout/stderr, latency, peak RAM/VRAM, runtime and artifact hashes.

A hash alone does not prove authorship or safety. Verify signatures/provenance separately where configured. Do not load untrusted pickle-based artifacts.

## 4. Independent Turkish quality report

At least two independent human evaluators who did not train the model must assess the same anonymized, versioned test set independently. Record separate ratings before adjudication.

Test strata: everyday Turkish and instruction following; factual questions with answer keys; reasoning; grammar, punctuation, fluency and natural phrasing; dialect/register and ambiguity; hallucination resistance and uncertainty; harmful requests, privacy, prompt injection and refusal boundaries; bias/fairness/accessibility; long context, Turkish characters, malformed input and interrupted generation.

For each item record test ID, expected behavior, model/version/hash, evaluator ID, correctness, fluency, safety, unsupported claims, severity, notes and adjudication. Publish method, limitations, disagreement rate and aggregate scores without exposing private test data.

Measure p50/p95 time-to-first-token and tokens/sec for text; end-to-end latency for each modality; peak RAM/VRAM; model load time; cold/warm runs; device/OS/driver/runtime; quantization; power mode and concurrent load. Repeat measurements and report sample count and spread. No unmeasured “fast”, “safe” or “production-ready” claims.

## 5. User-ready installer and model lifecycle

### First-run wizard
- Detect OS, CPU architecture, RAM, free disk, GPU/VRAM and supported acceleration.
- Explain required resources before download; show artifact size, source, license, version and SHA-256.
- Make local/private mode the default; cloud features require separate opt-in.
- Download to a temporary path, verify hash and compatibility, then install atomically.
- Support cancel/resume, progress, disk-space checks and a clear retry path.
- Never ask users to paste secrets into logs or send diagnostics automatically.

### Model status
Show installed model/version, local vs remote, active modality, verification state, device/runtime, last health check and whether network is disabled. Status must reflect real probes, not configuration alone.

### Upgrade and rollback
Keep immutable version directories. Stage new models separately; verify hashes, compatibility and smoke tests before activation. Switch the active pointer atomically only after checks pass. Keep the previous known-good version until explicit cleanup. Rollback must not delete user conversations/configuration. Record old/new hashes, reason and timestamp. Failed upgrades return to the previous verified model and explain why.

### Human-readable errors
Every error needs a stable code, short Turkish explanation, likely cause and safe next step. Redact prompts, tokens, keys, file contents and personal data by default.

## 6. Image, audio and video

Treat each modality as a separately tested capability:
- Images: supported formats/size limits, optional EXIF stripping, OCR/vision quality and privacy.
- Audio: speech-to-text and text-to-speech are separate; disclose recording/processing, show microphone permissions and offer text fallback.
- Video: distinguish sampled-frame understanding from continuous real-time audio/video. Record frame sampling, duration/size limits, audio handling and latency. Never claim real-time support if only frame extraction is implemented.
- Generated media: track model/version, provenance, output license, safety controls and resource limits.
- Each modality needs its own offline test, quality report, resource benchmark, failure-path tests and consent where capture is involved.

For best-in-class optional cloud vision/audio/video, use provider adapters behind the same model registry and privacy policy. Verify exact current model IDs and capabilities against official documentation at implementation/release time; do not invent IDs or silently fall back to older models. Local-only privacy must remain enforceable.

## 7. Security, privacy and release gates

A stable release is blocked until applicable gates pass:
- [ ] Data license/provenance and training/weight-distribution permissions reviewed.
- [ ] Secret scanning, dependency/SBOM/license scanning and static analysis pass.
- [ ] Model and tokenizer hashes verified; signed provenance checked where supported.
- [ ] Local-only mode demonstrated with network egress disabled and no hidden cloud fallback.
- [ ] Prompt injection, tool permissions, path traversal, malicious uploads, resource exhaustion and unsafe-output tests pass.
- [ ] Logs and telemetry are minimized/redacted; diagnostics require user action.
- [ ] Two independent Turkish evaluators complete reports and critical disagreements are adjudicated.
- [ ] Supported-device performance and resource thresholds are measured and published.
- [ ] Install, interrupted download, corrupt checkpoint, tokenizer mismatch, upgrade and rollback paths tested.
- [ ] Accessibility and Turkish UI copy reviewed.
- [ ] CI results and exact commit are green; if CI is unavailable, release is blocked rather than presumed green.
- [ ] Model card, changelog, limitations, hashes, installation and rollback instructions are published.

Critical safety, privacy or security failures block release regardless of aggregate score.

## 8. Implementation order

1. Model registry and policy enforcement, including local-only lock and explicit cloud consent.
2. Artifact integrity, tokenizer compatibility and offline network test.
3. Hardware-aware installer, status UI, model versioning and rollback.
4. Reproducible training after data rights and compute are approved.
5. Independent Turkish benchmark, two evaluators and real-device performance report.
6. Image/audio/video adapters, enabled only after capability, privacy and quality tests.
7. Release candidate after all gates pass, with evidence linked to exact commit and model hash.

## Honest current-state rule

This plan does not itself train a model, produce checkpoint weights, certify licenses, perform independent human evaluation, benchmark a physical device or prove offline inference. These require an approved corpus, suitable authorized machine, actual artifacts and recorded test evidence. Do not mark them complete until the evidence exists.
