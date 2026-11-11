-- Testcontainers로 띄운 DB에 db/roles/01_create_roles.sql 과 같은 준비를 한다 (슈퍼유저로 실행됨)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE ROLE tp_owner   LOGIN PASSWORD 'tp_owner';
CREATE ROLE tp_batch   LOGIN PASSWORD 'tp_batch';
CREATE ROLE tp_ai      LOGIN PASSWORD 'tp_ai';
CREATE ROLE tp_backend LOGIN PASSWORD 'tp_backend';
ALTER ROLE tp_ai SET default_transaction_read_only = on;
GRANT USAGE, CREATE ON SCHEMA public TO tp_owner;
GRANT USAGE         ON SCHEMA public TO tp_batch, tp_ai, tp_backend;
