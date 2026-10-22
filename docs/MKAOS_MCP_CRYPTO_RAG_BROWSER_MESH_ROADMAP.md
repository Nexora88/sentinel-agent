# MKAOS MCP, Crypto-RAG, Browser and Zero-Trust Mesh Roadmap

This document describes an incremental safety-first path. Source code or configuration alone does not mean a component is production-ready.

## 1. MCP: start with a read-only local server

Run from the repository root:

    MKAOS_MCP_WORKSPACE="$PWD" python -m core.mcp_server

The server uses stdio JSON-RPC and exposes one tool, workspace_read_text. It is read-only, bounded to approved project directories, rejects path traversal and common secret/key files, has no network listener, and cannot execute commands. Connect it only to a trusted local MCP client. The host/client must launch it with the intended working directory and environment.

This is a minimal foundation, not compatibility with every MCP tool. MCP servers are not automatically safe: tool descriptions and results are untrusted input. Require per-tool permissions and keep write, terminal and network capabilities disabled until separately reviewed. Protocol compatibility must be tested against the actual MCP client.

## 2. Encrypted vector storage

core/crypto_rag.py provides an opt-in AES-256-GCM encrypted SQLite vector store. It encrypts the embedding, document and metadata together; the database stores only an opaque ID, nonce and ciphertext. Similarity search decrypts bounded records locally and computes cosine similarity in-process.

It is a standalone storage primitive, NOT yet wired as a replacement for the existing Chroma/LangChain RAG pipeline. Do not claim existing Chroma files are encrypted by MKAOS_ENCRYPT_MEMORY_FILES. Migration needs an explicit export/encrypt/import tool, integrity/count comparison, backup and rollback plan, then a reviewed adapter switch. Existing plaintext vector stores remain sensitive.

Generate a key locally with Python calling core.crypto_rag.generate_key(), store it outside the database/repository, and set MKAOS_CRYPTO_RAG_KEY to its Base64 value. Never commit the key or paste it into chat. Losing it makes records unrecoverable. AES-GCM protects data at rest, not a compromised running process, memory dumps, backups, filenames, traffic or an attacker who also obtains the key. For stronger database-wide guarantees, consider encrypted volumes or SQLCipher separately. WAL/journal files and backup retention need storage testing too.

## 3. Browser automation: next phase, opt-in only

A Playwright worker should run in a separate digest-pinned container with a non-root user, read-only root filesystem, dropped Linux capabilities, seccomp, CPU/memory/PID/time limits, bounded screenshots, no host Docker socket, no credentials by default, and network egress restricted to an operator-approved target proxy. Browser automation must never be enabled by a generic ALLOW_SITE_SCANNING=true alone.

Before every navigation and redirect, enforce an explicit hostname/port allowlist, resolve and reject loopback/private/link-local/multicast/reserved IPs unless the operator explicitly authorizes a local lab target, and defend against DNS rebinding. Browser pages are untrusted; do not let page content authorize tool calls or leak cookies/secrets into model context. Screenshots and traces can contain sensitive data and need local retention limits. Keep the first release to owner-authorized passive mapping and human-approved interactions; no exploit payloads, credential attacks or destructive testing. The existing HTTP scanner is not equivalent to a browser agent. Playwright/browser-use has not been installed or tested by this change.

## 4. Zero-trust agent mesh

core/agent_mesh.py currently signs bounded data-only task envelopes; it does not provide a transport, confidentiality, mTLS, peer revocation or a live mesh.

Recommended order:
1. WireGuard tunnel with fixed peer public keys, narrow AllowedIPs, explicit firewall rules, and a key rotation/revocation runbook.
2. Application-layer mTLS with a private CA, per-agent identities, short-lived certificates, strict SAN-to-agent-ID mapping, and fail-closed certificate validation.
3. Keep Ed25519 message signatures, task allowlists, TTL and replay protection as an independent application authorization layer.
4. Only then evaluate hybrid/post-quantum key establishment and signatures. Existing optional liboqs code is experimental and does not automatically make the transport post-quantum secure. Define protocol versioning and test vectors before use.

WireGuard is a secure VPN tunnel, not itself a full application-level E2E protocol or a post-quantum signature system. Do not describe a tunnel as internet-disconnected; endpoints still use an IP network and security depends on routing/firewall configuration.

## 5. Acceptance gates

- Unit tests cover path traversal, secret-file rejection, MCP JSON-RPC behavior, encryption confidentiality/integrity, wrong-key failure and input limits.
- MCP client interoperability is tested against a pinned client version.
- Crypto-RAG migration tests prove every record count/hash matches and plaintext vector files are removed only after verified backup and explicit approval.
- Browser worker is tested against a local intentionally vulnerable lab only, with network egress and SSRF regression tests.
- Mesh tests include invalid/missing/revoked certificates, wrong SAN, replay, expired tasks, blocked routes, key rotation and optional PQ interoperability vectors.
- No automatic merge, deployment or live scanning; all external effects require human approval.
