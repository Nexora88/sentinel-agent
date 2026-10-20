# MKAOS Night Watch, Voice and Media — implementation status

This document separates working contracts from capabilities that still need a real backend or device validation.

## Night Watch agent

- Schedule: GitHub Actions cron `0 0 * * *` UTC, which corresponds to 03:00 in Türkiye (UTC+3). GitHub may start scheduled jobs late during load.
- Scope: only projects explicitly enabled in `config/mkaos-agent-projects.json`.
- Current allowlist: this repository only. Other repositories must not be added until their owners have approved access and the runner has the right permissions.
- Checks: Python compilation, Python unit tests, Rust tests when the manifest/toolchain exists, Git whitespace checks, and a conservative tracked-file secret-pattern pass.
- Output: a machine-readable report artifact and the existing failure issue flow.
- Safety: the agent is read-only. It does not silently rewrite files, push branches, merge PRs, download models, or train models. A detected problem should become a reproducible issue and then a tested, reviewable PR.
- This is an automated quality/security watcher, not yet a self-modifying coding agent. Automated patch drafting and iterative repair are a later stage requiring a bounded code-writer, isolated worktree, regression tests, diff review, and approval before merge.

## Turkish voice engine

The merged voice work provides local Piper TTS integration contracts, separate Turkish male/female speaking profiles, prosody controls and a bounded speed setting. Model weights are not stored in this repository, so the actual Turkish voice models must be installed separately. A high-quality claim is not justified until both voices are listened to on target hardware and tested against a Turkish pronunciation corpus. No public cloud TTS fallback is intended.

## Image generation and editing

The media bridge already distinguishes offline canvas/poster generation from neural image generation. The local Stable Diffusion adapter is enabled only when its self-hosted endpoint is configured. Configuration alone does not prove the endpoint is healthy; deployment validation should call a small test prompt, verify the returned image and record latency, resolution, memory and failure details. Image editing and background replacement similarly require a configured local generator.

## Video

Three capabilities must not be conflated:

1. **Storyboard/slideshow video** — locally assembled frames/audio/video through existing canvas/ffmpeg paths.
2. **Video understanding** — bounded local video-frame sampling followed by the configured local vision model. This does not establish full temporal or motion understanding.
3. **Neural text-to-video** — currently only an adapter contract; it is unavailable until an explicitly local/self-hosted model backend implementing `generate_video` is installed and validated.

The next media milestone is a backend-health and quality benchmark suite: deterministic test prompts, output-file validation, Turkish captions/audio sync checks, duration/resolution checks, latency and peak-memory measurements, and explicit “unavailable” states when no model is configured. No public service should be silently used as a fallback.

## Completion criteria

- Night Watch reports the exact commit, checked project, check results and links to its logs.
- Every proposed fix gets a regression test and passes CI before a human-reviewed PR can merge.
- Voice quality is evaluated on real Turkish utterances and the intended hardware.
- Image/video capabilities report runtime readiness, not merely the presence of a URL or adapter class.
- No model is described as trained, locally installed or high quality without verifiable artifacts and measurements.
