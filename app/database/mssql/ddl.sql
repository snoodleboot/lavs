-- LAVS core schema (SQL Server / T-SQL dialect).
-- Kept intentionally close to the DuckDB, PostgreSQL, and MySQL dialects: ULID
-- identifiers are stored as VARCHAR and foreign keys reference the parent
-- table's id. Column names are identical across dialects so the query layer
-- (which speaks a single, dialect-agnostic statement set) is unchanged.
--
-- SQL Server-specific accommodations vs the other dialects:
--   * SQL Server has no `CREATE TABLE IF NOT EXISTS`, so every table is guarded
--     with `IF OBJECT_ID(N'table', N'U') IS NULL <newline> CREATE TABLE ...`.
--     The guard and its CREATE carry no interior `;`, so the statement splitter
--     (which splits on `;`) keeps each guarded create as ONE batch that the IF
--     and CREATE execute together — making re-running init_schema a no-op.
--   * `TIMESTAMP` in SQL Server is a binary row-version (ROWVERSION), NOT a
--     datetime, so timestamps are DATETIME2 with `DEFAULT SYSUTCDATETIME()`.
--     The app binds naive UTC instants; DATETIME2 stores them verbatim.
--   * Indexed/PK/unique/FK/hash string columns are VARCHAR(255) (ULIDs, emails,
--     tokens); free-text description/notes are NVARCHAR(MAX) (avoiding the
--     deprecated TEXT type) so the full Unicode range is storable.
--   * Foreign keys are declared as table-level constraints (matching the MySQL
--     and PostgreSQL dialects), and the composite `release_components` primary
--     key is preserved.
--   * The PostgreSQL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS base_version`
--     migration is omitted (as in the MySQL dialect): it is a legacy upgrade for
--     databases predating the column, and this backend is new (the column is
--     always present via CREATE TABLE).
--
-- pymssql's cursor runs one batch at a time, so MssqlBackend.init_schema splits
-- this script on ';' and runs each statement individually.

IF OBJECT_ID(N'products', N'U') IS NULL
CREATE TABLE products (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description NVARCHAR(MAX),
    base_version VARCHAR(255) NOT NULL DEFAULT '0.0.0',
    bump_policy VARCHAR(255) NOT NULL DEFAULT 'legacy',
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

IF OBJECT_ID(N'components', N'U') IS NULL
CREATE TABLE components (
    id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    kind VARCHAR(255) NOT NULL CHECK (kind IN ('library', 'service', 'ui', 'cli')),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

IF OBJECT_ID(N'versions', N'U') IS NULL
CREATE TABLE versions (
    id VARCHAR(255) PRIMARY KEY,
    component_id VARCHAR(255) NOT NULL,
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    prerelease VARCHAR(255),
    status VARCHAR(255) DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'rolled_back')),
    created_at DATETIME2 DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (component_id) REFERENCES components(id)
);

IF OBJECT_ID(N'releases', N'U') IS NULL
CREATE TABLE releases (
    id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    product_version VARCHAR(255) NOT NULL,
    label VARCHAR(255),
    notes NVARCHAR(MAX),
    idempotency_key VARCHAR(255),
    bump_level VARCHAR(255),
    bump_rationale NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

IF OBJECT_ID(N'release_components', N'U') IS NULL
CREATE TABLE release_components (
    release_id VARCHAR(255) NOT NULL,
    component_id VARCHAR(255) NOT NULL,
    version_id VARCHAR(255) NOT NULL,
    change_level VARCHAR(255),
    PRIMARY KEY (release_id, component_id),
    FOREIGN KEY (release_id) REFERENCES releases(id)
);

-- P9: product dependency graph — intra-product edges "from depends on to".
-- Guarded with IF OBJECT_ID (T-SQL has no CREATE TABLE IF NOT EXISTS); the
-- guard and CREATE carry no interior ';' so the splitter keeps them one batch.
-- Self-edge, cross-product and cycle rejection are enforced in the application
-- layer (portable, no recursive CTE). As with base_version, the P9 columns on
-- the pre-existing products/releases/release_components tables are present here
-- via CREATE for a fresh database; the idempotent add-column upgrade for a
-- database predating P9 is handled out-of-band (F-4).
IF OBJECT_ID(N'component_dependencies', N'U') IS NULL
CREATE TABLE component_dependencies (
    id VARCHAR(255) NOT NULL PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    from_component_id VARCHAR(255) NOT NULL,
    to_component_id VARCHAR(255) NOT NULL,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_component_dependencies UNIQUE (product_id, from_component_id, to_component_id),
    CONSTRAINT fk_cd_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_cd_from FOREIGN KEY (from_component_id) REFERENCES components(id),
    CONSTRAINT fk_cd_to FOREIGN KEY (to_component_id) REFERENCES components(id)
);

-- Auth (P4): password/session users and their opaque, hashed tokens.
-- Passwords are stored as argon2id hashes; session and verification tokens are
-- stored only as their SHA-256 hashes (the raw token is never persisted).
IF OBJECT_ID(N'users', N'U') IS NULL
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'disabled')),
    edition VARCHAR(255),
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

-- expires_at / consumed_at on the two auth tables below are naive DATETIME2
-- columns holding UTC instants: SessionService and VerificationTokenRepository
-- compute time as datetime.now(UTC) with tzinfo stripped before binding, so
-- values round-trip verbatim regardless of the host or session time zone.
IF OBJECT_ID(N'sessions', N'U') IS NULL
CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME(),
    expires_at DATETIME2 NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

IF OBJECT_ID(N'email_verification_tokens', N'U') IS NULL
CREATE TABLE email_verification_tokens (
    token_hash VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    expires_at DATETIME2 NOT NULL,
    consumed_at DATETIME2,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
