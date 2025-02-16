CREATE TABLE IF NOT EXISTS Versions (
    major INTEGER,
    minor INTEGER,
    patch INTEGER,
    product_name VARCHAR,
    id INTEGER PRIMARY KEY
);

CREATE SEQUENCE IF NOT EXISTS version_id_seq START 1;