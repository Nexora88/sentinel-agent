# MKAOS MCP, Crypto-RAG, Browser and Zero-Trust Mesh Roadmap

This document describes an incremental safety-first path. Source code or configuration alone does not mean a component is production-ready.

## 1. MCP: start with a read-only local server

Run from the repository root:

    MKAOS_MCP_WORKSPACE="$PWD" python -m core.mcp_server

The server uses stdio JSON-RPC and exposes one tool, workspace_read_text. It is read-only, bounded to approved project directories, rejects path traversal and common secret/key files, has no network listener, and cannot execute commands. Connect it only to a trusted local MCP client. The host/client must launch it with the intended working directory and environment.

This is a minimal foundation, not compatibility with every MCP tool. MCP servers are not automatically safe: tool descriptions and results are untrusted input. Require per-tool permissions and keep write, terminal and network capabilities disabled until separately reviewed. Protocol compatibility must be tested against the actual MCP client.

## 2. Encrypted vector storage

core/crypto_rag.py provides an opt-in AES-256-GCM encrypted SQLite vector store. It encrypts the embedding, document and metadata together; the database stores only an opaque ID, nonce and ciphertext. Similarity search decrypts bounded records locally and computes cosine similarity in-process.

It is now integrated into core/rag.py as an opt-in backend via SEKA_RAG_STORAGE_BACKEND=crypto-sqlite; Chroma remains the default. The encrypted backend requires an explicit SEKA_CRYPTO_RAG_PATH outside the Chroma directory and MKAOS_CRYPTO_RAG_KEY, and currently supports local mkaos-native/local-semantic embeddings only. The non-destructive tools/migrate_crypto_rag.py utility requires stopped writers, creates a verified backup, copies bounded batches, decrypts and compares every document/metadata/embedding, checks source/destination counts, and never deletes source data. See docs/MKAOS_CRYPTO_RAG_MIGRATION.md. Existing plaintext vector stores remain sensitive until a separately reviewed switch and explicit approved cleanup.

Generate a key locally with Python calling core.crypto_rag.generate_key(), store it outside the database/repository, and set MKAOS_CRYPTO_RAG_KEY to its Base64 value. Never commit the key or paste it into chat. Losing it makes records unrecoverable. AES-GCM protects data at rest, not a compromised running process, memory dumps, backups, filenames, traffic or an attacker who also obtains the key. For stronger database-wide guarantees, consider encrypted volumes or SQLCipher separately. WAL/journal files and backup retention need storage testing too.

## 3. Browser automation: isolated screenshot-only first stage

Dockerfile.browser, docker-compose.browser.yml, and scripts/browser_screenshot.py add a separate non-root Playwright worker and local static fixture. The browser network is internal-only with no host ports, no Docker socket, no application credentials, read-only root filesystem, dropped capabilities, no-new-privileges, and CPU/memory/PID limits. The worker exposes navigation and screenshot capture only, checks an exact hostname allowlist, and rechecks each request/redirect. See docs/MKAOS_BROWSER_ISOLATION.md.

This is a local lab foundation, not a live scanner or production-ready browser agent. The base image is version-tagged but still needs a reviewed immutable digest before production use. DNS rebinding, unusual port, IPv4/IPv6, browser escape, and resource-exhaustion tests remain required. Live scanning and interactions beyond navigation/screenshot stay disabled and require explicit human approval.

## 4. Zero-trust agent mesh

core/agent_mesh.py signs bounded data-only task envelopes. core/mesh_tls.py now provides TLS 1.3+ client/server context builders and a post-handshake URI-SAN agent-ID allowlist plus SHA-256 fingerprint revocation check. Neither module opens a listener, distributes revocations, or proves a live mesh is deployed. The WireGuard runbook is in docs/MKAOS_WIREGUARD_MESH_ROLLOUT.md.

Recommended order:
1. WireGuard tunnel with fixed peer public keys, narrow AllowedIPs, explicit firewall rules, and a key rotation/revocation runbook.
2. Application-layer mTLS with a private CA, per-agent identities, short-lived certificates, strict SAN-to-agent-ID mapping, and fail-closed certificate validation.
3. Keep Ed25519 message signatures, task allowlists, TTL and replay protection as an independent application authorization layer.
4. Only then evaluate hybrid/post-quantum key establishment and signatures. Existing optional liboqs code is experimental and does not automatically make the transport post-quantum secure. Define protocol versioning and test vectors before use.

WireGuard is a secure VPN tunnel, not itself a full application-level E2E protocol or a post-quantum signature system. Do not describe a tunnel as internet-disconnected; endpoints still use an IP network and security depends on routing/firewall configuration.

## 5. Acceptance gates

- Unit tests cover path traversal, secret-file rejection, MCP JSON-RPC behavior, encryption confidentiality/integrity, wrong-key failure and input limits.
- MCP client interoperability is tested against a pinned client version.
- Crypto-RAG migration tests prove record counts and exact decrypted content/metadata/embedding equality. Source plaintext is never removed by the migration utility; any later cleanup requires a verified restorable backup and explicit approval.
- Browser worker is currently limited to a benign local fixture. Expand only after network-egress, SSRF, DNS rebinding, redirect, timeout, and resource-limit regression tests pass.
- Mesh tests include invalid/missing/revoked certificates, wrong SAN, replay, expired tasks, blocked routes, key rotation and optional PQ interoperability vectors.
- No automatic merge, deployment or live scanning; all external effects require human approval.
