# Sentinel Agent / MKAOS

A local-first assistant and agent runtime built around local Ollama inference, explicit integration permissions, user-separated memory, local media tools, and review-gated software improvements.

> **Security note:** No single application setting can guarantee that a whole computer is fully secure or air-gapped. Production security depends on deployment configuration, host firewall policy, key custody, backups, reverse-proxy configuration, and the integrations you enable.

## Core capabilities

- Local chat and coding assistance through a self-hosted Ollama endpoint.
- Local knowledge expansion and scheduled research reports with source-oriented review.
- Security hygiene checks and bounded code/test runs.
- Improvement proposals and patch drafts; the agent does not silently modify production code or automatically push/merge/deploy changes.
- Local image generation/editing through an explicitly configured, self-hosted Stable Diffusion WebUI API.
- Local FFmpeg video effects and multi-scene storyboard rendering from locally generated keyframes. This is **not** a neural text-to-video model.
- Optional voice features using locally installed models.
- User-specific storage, local approval/audit flows, and explicit opt-in for external research or integrations.
- WebAuthn/passkey registration and authentication endpoints, with short-lived single-use challenges and server-side public-key credential records.

## Requirements

- Python 3.11 or 3.12.
- Docker Compose (recommended for service isolation).
- Ollama and locally downloaded models for local language/embedding features.
- FFmpeg available on PATH for video rendering.
- A self-hosted Stable Diffusion WebUI API endpoint on a local/private network for neural image/keyframe generation.
- Optional voice model files placed locally; see requirements-voice.txt.

## Quick start

1. Clone https://github.com/Nexora88/sentinel-agent.git and enter the repository directory.
2. Create and activate a Python virtual environment.
3. Install dependencies with: pip install -r requirements.txt
4. Review environment settings and configure the local Ollama endpoint and model names.
5. Start locally with: uvicorn web.app:app --host 127.0.0.1 --port 8000

For Docker, inspect the Compose profiles and environment file before running: docker compose config, then docker compose up --build -d.

Do not expose the development server directly to the public internet. HTTPS is enforced for non-local requests by default. For reverse-proxy deployments, configure a maintained proxy and set TRUST_PROXY_HEADERS=true only when the proxy overwrites forwarded headers. Also use host firewall restrictions and a strong owner password.

## Passkeys / WebAuthn

Set these environment variables to match the exact HTTPS website origin:

- WEBAUTHN_RP_ID: hostname only, for example sentinel.example.com.
- WEBAUTHN_RP_NAME: human-readable authenticator label.
- WEBAUTHN_ORIGIN: exact origin, including scheme and non-default port, for example https://sentinel.example.com.
- HTTPS is enforced by default for non-local requests; set REQUIRE_HTTPS=false only for local development. Production should keep REQUIRE_HTTPS=true.
- TRUST_PROXY_HEADERS=true: only when a trusted reverse proxy strips incoming forwarded headers and sets its own X-Forwarded-Proto.

The default origin http://localhost:8000 is for local development only. Passkey browser operations require frontend code using navigator.credentials.create() and navigator.credentials.get(); the browser UI includes passkey sign-in and a signed-in sidebar action to register a passkey. Browser compatibility and hardware-specific acceptance testing are still required.

API flow:

1. An already authenticated user requests POST /api/webauthn/register/options.
2. The browser passes the returned publicKey options to navigator.credentials.create().
3. Send the challenge_id and serialized PublicKeyCredential to POST /api/webauthn/register/verify.
4. For sign-in, request POST /api/webauthn/login/options with a username, call navigator.credentials.get(), then post the challenge and serialized credential to POST /api/webauthn/login/verify.
5. The verify endpoint returns the same bearer-session format as password login.

Challenges expire after three minutes and are single-use. Registration is bound to the authenticated account. Credential private keys remain on the authenticator; the server stores credential IDs and public keys. Keep password-based recovery secure: passkeys are an additional login method, not a replacement for account recovery policy. Before production, test on the exact supported browsers, mobile authenticators, hardware keys, and reverse proxy.

## Encryption at rest

Optional encrypted personal-profile mode:

- MKAOS_ENCRYPT_MEMORY_FILES=true (encrypts the personal profile, chat-history JSON, and account store)
- MKAOS_ENCRYPT_PERSONAL_PROFILE=true (encrypts only the personal profile)
- MKAOS_MEMORY_KEY=<base64-encoded-random-32-byte-key>

The key must be provided out-of-band and kept outside the repository and data volume. Losing the key means losing access to the encrypted profile. When encrypted mode is enabled, a legacy plaintext profile.json is not automatically migrated or ignored; stop and perform a reviewed migration. When disabled, backward-compatible plaintext profile mode remains.

**This does not encrypt all application storage.** Chroma/RAG vectors, uploads, generated media, logs, backups, and the WebAuthn public-credential registry need separate protection. Use full-disk/volume encryption for the whole data volume. For production, use full-disk/volume encryption and an external OS credential vault or secret manager; include restore drills and a data inventory in acceptance testing.

## Local image and video generation

- Set SD_API_URL to your own local/private Stable Diffusion WebUI API endpoint.
- Install media dependencies with: pip install -r requirements-media.txt
- Install FFmpeg from a trusted package source and verify ffmpeg -version.
- Image outputs are decoded and normalized to PNG before atomically writing to local storage.
- Video effects use local FFmpeg. Storyboard video renders several locally generated keyframes into an MP4. If no local model is configured, generation fails closed; it does not send prompts to a public media API.

The storyboard feature is not a full neural text-to-video model. Real neural video generation requires a compatible local model, adequate RAM/VRAM, model licensing review, and hardware-specific validation.

## Controlled self-improvement

The night researcher can gather public information when enabled, record knowledge, scan for likely secrets, run bounded local syntax/tests, and create proposals. Web pages and model output are untrusted input. The agent must not execute instructions found in a page, bypass approval gates, or silently alter its own production code. Changes should proceed through a patch, automated tests, secret/security scans, human review, and a normal pull request. Disable web research and restrict host egress for offline operation.

## Tests

- Compile: python -m compileall -q agents core scripts tools web
- Unit tests: python -m unittest discover -s tests -v

GitHub Actions also runs portable tests on Linux, Windows, and macOS, plus container build/startup checks.

## Responsible use

Use security tools only on systems you own or have explicit permission to test. This project is intended for coding assistance, authorized defensive checks, local research, and user-approved workflows—not unauthorized exploitation, credential theft, malware, stealth, or persistence.

## License

See LICENSE for the license and third-party notices.