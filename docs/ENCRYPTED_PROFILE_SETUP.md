# Encrypted Personal Profile Setup

The personal profile can optionally be stored as an AES-256-GCM authenticated encrypted file. This is an additional protection for `profile.json`; it does **not** encrypt Chroma/RAG vectors, conversation history, uploads, logs, backups, or every other file under `memory/`.

## Enable it

1. Stop the application and make a protected backup of the existing profile.
2. Provide a random 32-byte key encoded as standard or URL-safe Base64 through `MKAOS_MEMORY_KEY`. Keep the key outside the repository and outside the data directory; use an OS credential vault or secret manager for deployments.
3. Set `MKAOS_ENCRYPT_PERSONAL_PROFILE=true`.
4. Start the app and verify that `memory/personal/profile.enc` is created and profile read/write works.
5. Back up the key separately. Losing it means the encrypted profile cannot be recovered.

## Existing plaintext profiles

The application intentionally refuses to silently ignore or automatically migrate `profile.json` when encrypted mode is enabled. If a plaintext profile already exists, stop and plan an explicit, reviewed migration. Do not delete the old file until the encrypted profile has been verified and a protected backup is confirmed.

When encrypted mode is disabled or unset, the existing `profile.json` behavior remains for backward compatibility. The profile's encryption mode is a deployment choice, not a claim that all application memory is encrypted.

## Validation

Run:

```bash
python -m unittest discover -s tests -p 'test_encrypted_personal_profile.py' -v
python -m unittest discover -s tests -p 'test_encrypted_store.py' -v
python -m unittest discover -s tests -p 'test_local_media.py' -v
```

The CI suite also checks the default profile behavior and local media boundaries. Production deployment still requires a full storage inventory, external key-management policy, backup/recovery drill, and per-tenant isolation review.
