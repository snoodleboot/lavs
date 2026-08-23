-- LAVS core schema (DuckDB dialect).
-- ULID identifiers are stored as VARCHAR; foreign keys are modelled as plain
-- VARCHAR columns referencing the parent table's id.

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    base_version VARCHAR NOT NULL DEFAULT '0.0.0',
    bump_policy VARCHAR NOT NULL DEFAULT 'legacy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Idempotently upgrade databases created before base_version existed.
ALTER TABLE products ADD COLUMN IF NOT EXISTS base_version VARCHAR DEFAULT '0.0.0';
-- P9: per-product derived-bump policy. Existing rows default to 'legacy'
-- (byte-identical to the pre-P9 minor bump); new products are created 'default'.
ALTER TABLE products ADD COLUMN IF NOT EXISTS bump_policy VARCHAR DEFAULT 'legacy';

CREATE TABLE IF NOT EXISTS components (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL CHECK (kind IN ('library', 'service', 'ui', 'cli'))
);

CREATE TABLE IF NOT EXISTS versions (
    id VARCHAR PRIMARY KEY,
    component_id VARCHAR NOT NULL REFERENCES components(id),
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    prerelease VARCHAR,
    status VARCHAR DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'rolled_back')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS releases (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    product_version VARCHAR NOT NULL,
    label VARCHAR,
    notes VARCHAR,
    idempotency_key VARCHAR,
    bump_level VARCHAR,
    bump_rationale VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- P9: the derived bump magnitude and its explanation, populated at cut time.
ALTER TABLE releases ADD COLUMN IF NOT EXISTS bump_level VARCHAR;
ALTER TABLE releases ADD COLUMN IF NOT EXISTS bump_rationale VARCHAR;

CREATE TABLE IF NOT EXISTS release_components (
    release_id VARCHAR NOT NULL REFERENCES releases(id),
    component_id VARCHAR NOT NULL,
    version_id VARCHAR NOT NULL,
    change_level VARCHAR,
    PRIMARY KEY (release_id, component_id)
);
-- P9: each component's own change classification within the release.
ALTER TABLE release_components ADD COLUMN IF NOT EXISTS change_level VARCHAR;

-- P9: product dependency graph — intra-product edges "from depends on to".
-- Product-scoped; the unique key forbids duplicate edges. Self-edge, cross-
-- product and cycle rejection are enforced in the application layer (portable,
-- no recursive CTE, so the identical guard holds on every backend).
CREATE TABLE IF NOT EXISTS component_dependencies (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    from_component_id VARCHAR NOT NULL REFERENCES components(id),
    to_component_id VARCHAR NOT NULL REFERENCES components(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (product_id, from_component_id, to_component_id)
);

-- Auth (P4): password/session users and their opaque, hashed tokens.
-- Passwords are stored as argon2id hashes; session and verification tokens are
-- stored only as their SHA-256 hashes (the raw token is never persisted).
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'disabled')),
    edition VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- expires_at / consumed_at on the two auth tables below are naive TIMESTAMP
-- columns holding UTC instants: SessionService and VerificationTokenRepository
-- compute time as datetime.now(UTC) with tzinfo stripped before binding, so
-- values round-trip verbatim regardless of the host or session time zone.
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    token_hash VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_hash VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP
);
