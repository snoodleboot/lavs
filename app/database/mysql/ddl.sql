-- LAVS core schema (MySQL / InnoDB dialect).
-- Kept intentionally close to the DuckDB and PostgreSQL dialects: ULID
-- identifiers are stored as VARCHAR and foreign keys reference the parent
-- table's id. Column names are identical across dialects so the query layer
-- (which speaks a single, dialect-agnostic statement set) is unchanged.
--
-- MySQL-specific accommodations vs the PostgreSQL dialect:
--   * Every table is InnoDB / utf8mb4 so CHECK constraints and foreign keys are
--     enforced and the full Unicode range is storable.
--   * Indexed/PK/unique string columns carry an explicit length (VARCHAR(255));
--     MySQL requires a length on such columns. VARCHAR(255) utf8mb4 is 1020
--     bytes, comfortably under InnoDB's 3072-byte index-key limit.
--   * Timestamps are DATETIME (not TIMESTAMP): the app binds naive UTC instants
--     and DATETIME stores them verbatim, avoiding TIMESTAMP's session-timezone
--     conversion and 1970 epoch range limits.
--   * Foreign keys are declared as table-level constraints; MySQL parses but
--     silently ignores column-level inline REFERENCES, so table-level clauses
--     are required to actually enforce them (matching PostgreSQL's semantics).
--   * The PostgreSQL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS base_version`
--     migration is omitted: it is a legacy upgrade for databases predating the
--     column, MySQL has no idempotent ADD COLUMN, and this backend is new (the
--     column is always present via CREATE TABLE).
--
-- MySQL rejects a multi-statement `execute` through PyMySQL's single-statement
-- cursor, so MySqlBackend.init_schema splits this script on ';' and runs each
-- statement individually. Every CREATE TABLE is idempotent (IF NOT EXISTS), so
-- this is safe to run on every boot.

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_version VARCHAR(255) NOT NULL DEFAULT '0.0.0',
    bump_policy VARCHAR(255) NOT NULL DEFAULT 'legacy',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS components (
    id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    kind VARCHAR(255) NOT NULL CHECK (kind IN ('library', 'service', 'ui', 'cli')),
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS versions (
    id VARCHAR(255) PRIMARY KEY,
    component_id VARCHAR(255) NOT NULL,
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    prerelease VARCHAR(255),
    status VARCHAR(255) DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'rolled_back')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (component_id) REFERENCES components(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS releases (
    id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    product_version VARCHAR(255) NOT NULL,
    label VARCHAR(255),
    notes TEXT,
    idempotency_key VARCHAR(255),
    bump_level VARCHAR(255),
    bump_rationale TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS release_components (
    release_id VARCHAR(255) NOT NULL,
    component_id VARCHAR(255) NOT NULL,
    version_id VARCHAR(255) NOT NULL,
    change_level VARCHAR(255),
    PRIMARY KEY (release_id, component_id),
    FOREIGN KEY (release_id) REFERENCES releases(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- P9: product dependency graph — intra-product edges "from depends on to".
-- Table-level FKs (InnoDB ignores inline REFERENCES). The three-column unique
-- key is 3*255*4 = 3060 bytes utf8mb4, under InnoDB's 3072-byte index limit.
-- Self-edge, cross-product and cycle rejection are enforced in the application
-- layer (portable, no recursive CTE). As with base_version above, the P9
-- columns on the pre-existing products/releases/release_components tables are
-- present here via CREATE for a fresh database; the idempotent add-column
-- upgrade for a database predating P9 is handled out-of-band (F-4), MySQL
-- having no in-DDL `ADD COLUMN IF NOT EXISTS`.
CREATE TABLE IF NOT EXISTS component_dependencies (
    id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    from_component_id VARCHAR(255) NOT NULL,
    to_component_id VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (product_id, from_component_id, to_component_id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (from_component_id) REFERENCES components(id),
    FOREIGN KEY (to_component_id) REFERENCES components(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Auth (P4): password/session users and their opaque, hashed tokens.
-- Passwords are stored as argon2id hashes; session and verification tokens are
-- stored only as their SHA-256 hashes (the raw token is never persisted).
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'disabled')),
    edition VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- expires_at / consumed_at on the two auth tables below are naive DATETIME
-- columns holding UTC instants: SessionService and VerificationTokenRepository
-- compute time as datetime.now(UTC) with tzinfo stripped before binding, so
-- values round-trip verbatim regardless of the host or session time zone.
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_hash VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    consumed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
