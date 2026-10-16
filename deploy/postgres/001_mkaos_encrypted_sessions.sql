-- MKAOS persistent encrypted session/memory foundation.
-- Apply with a migration role; application connections must use a non-superuser role
-- without BYPASSRLS. Payloads are app-layer authenticated ciphertext, never plaintext.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS mkaos_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata_ciphertext BYTEA,
    UNIQUE (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS mkaos_sessions_tenant_updated
    ON mkaos_sessions (tenant_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS mkaos_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    session_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content_ciphertext BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, session_id)
        REFERENCES mkaos_sessions (tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS mkaos_messages_tenant_session_time
    ON mkaos_messages (tenant_id, session_id, created_at, id);

CREATE TABLE IF NOT EXISTS mkaos_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    memory_kind TEXT NOT NULL DEFAULT 'fact',
    payload_ciphertext BYTEA NOT NULL,
    embedding_ciphertext BYTEA,
    embedding_model_id TEXT,
    source_session_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, source_session_id)
        REFERENCES mkaos_sessions (tenant_id, id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS mkaos_memories_tenant_updated
    ON mkaos_memories (tenant_id, updated_at DESC);

ALTER TABLE mkaos_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE mkaos_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE mkaos_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE mkaos_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE mkaos_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE mkaos_memories FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS mkaos_sessions_tenant_isolation ON mkaos_sessions;
CREATE POLICY mkaos_sessions_tenant_isolation ON mkaos_sessions
    USING (tenant_id = current_setting('mkaos.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('mkaos.tenant_id', true));
DROP POLICY IF EXISTS mkaos_messages_tenant_isolation ON mkaos_messages;
CREATE POLICY mkaos_messages_tenant_isolation ON mkaos_messages
    USING (tenant_id = current_setting('mkaos.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('mkaos.tenant_id', true));
DROP POLICY IF EXISTS mkaos_memories_tenant_isolation ON mkaos_memories;
CREATE POLICY mkaos_memories_tenant_isolation ON mkaos_memories
    USING (tenant_id = current_setting('mkaos.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('mkaos.tenant_id', true));

-- Every application transaction must execute:
--   SET LOCAL mkaos.tenant_id = '<authenticated opaque tenant id>';
-- Do not set this from an untrusted request field. Derive it from verified auth.
-- Encryption keys belong in a secret manager or protected local secret file, never SQL.
