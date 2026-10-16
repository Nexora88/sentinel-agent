# MKAOS PostgreSQL persistence and tenant isolation

This migration is the first persistent-storage foundation, not a claim that the whole application has switched from Chroma/files to PostgreSQL. It creates session, message, and memory records with encrypted payload columns, tenant-scoped foreign keys, indexes, and PostgreSQL row-level security (RLS).

## Required application contract

1. Authenticate the caller before deriving an opaque tenant ID; never accept the tenant identity as an authoritative client-supplied field.
2. Start a transaction and set the transaction-local tenant scope from the verified identity. All queries must be tenant-scoped even though RLS is also enabled.
3. Use a non-superuser database role with no BYPASSRLS. Table owners should not be used for runtime requests; FORCE ROW LEVEL SECURITY is a second layer, not a replacement for a correct role.
4. Encrypt message, metadata, memory, and any future embedding payloads in the application before writing them to BYTEA. Use authenticated encryption with unique nonces and associated data binding the ciphertext to tenant/table/record. Keep keys outside the database and rotate/recover them under an explicit policy.
5. Never log plaintext prompts, memory payloads, encryption keys, or connection secrets. TLS is required for remote PostgreSQL; offline local deployments may use a Unix socket.
6. Do not scale to multiple replicas until migration rollout, key distribution/rotation, transaction semantics, idempotency, backup restore, RLS bypass tests, and concurrent-write behavior have been validated.

## Current scope and remaining integration

Migration: deploy/postgres/001_mkaos_encrypted_sessions.sql

Install the optional driver after the base project dependencies: `pip install -r requirements-postgres.txt`.

The existing local Chroma/RAG and personal-memory stores are not automatically migrated by this SQL. A runtime adapter still needs to connect using an approved PostgreSQL driver, apply transaction-local tenant context on every operation, encrypt/decrypt payloads, handle migrations and retry/idempotency, and provide backup/restore. The embedding column is encrypted opaque data; it is not a vector index and does not make retrieval semantic by itself. A later Rust local encoder and a separately evaluated vector-index design remain required.

## Key custody

Do not place encryption keys in the migration, database, source control, container image, or logs. Use a protected secret store or owner-managed local secret. If the key is missing, fail closed rather than storing plaintext. Database-at-rest encryption alone does not replace application-layer payload encryption when database administrators are outside the trust boundary.
