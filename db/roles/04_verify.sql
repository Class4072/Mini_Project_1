-- =============================================================
-- 04_verify.sql — 계정과 권한이 DATABASE.md 6장대로 들어갔는지 확인 (읽기만 한다)
--
--   psql -h <호스트> -p <포트> -U <관리자> -d <DB이름> -f db/roles/04_verify.sql
--
-- [2], [3], [5]는 비어 있어야 정상이다.
-- =============================================================
\pset footer off

\echo
\echo '[1] 서비스 계정 — 테이블 생성은 tp_owner만, 계정 설정에 tp_ai만 default_transaction_read_only=on'
SELECT r.rolname                                                   AS "계정",
       r.rolcanlogin                                               AS "로그인",
       r.rolsuper                                                  AS "슈퍼유저",
       has_database_privilege(r.oid, current_database(), 'CONNECT') AS "DB 접속",
       has_schema_privilege(r.oid, 'public', 'USAGE')              AS "스키마 사용",
       has_schema_privilege(r.oid, 'public', 'CREATE')             AS "테이블 생성",
       COALESCE((SELECT array_to_string(s.setconfig, ', ')
                 FROM pg_db_role_setting s
                 WHERE s.setrole = r.oid AND s.setdatabase = 0), '') AS "계정 설정"
FROM pg_roles r
WHERE r.rolname IN ('tp_owner', 'tp_batch', 'tp_ai', 'tp_backend')
ORDER BY array_position(ARRAY['tp_owner', 'tp_batch', 'tp_ai', 'tp_backend'], r.rolname::text);

\echo
\echo '[2] PUBLIC(모든 계정)에 남은 권한 — 02 이후에는 비어 있어야 함'
SELECT 'DB ' || d.datname AS "대상", a.privilege_type AS "권한"
FROM pg_database d, aclexplode(COALESCE(d.datacl, acldefault('d', d.datdba))) a
WHERE d.datname = current_database() AND a.grantee = 0
UNION ALL
SELECT 'schema public', a.privilege_type
FROM pg_namespace n, aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner))) a
WHERE n.nspname = 'public' AND a.grantee = 0;

\echo
\echo '[3] 테이블 권한이 DATABASE.md 6.2와 다른 곳 — 비어 있으면 일치'
WITH expected(role, tbl, privs) AS (VALUES
    ('tp_batch',   'region',             'SELECT, INSERT, UPDATE'),
    ('tp_batch',   'tour_places',        'SELECT, INSERT, UPDATE'),
    ('tp_batch',   'tour_place_details', 'SELECT, INSERT, UPDATE'),
    ('tp_batch',   'tour_place_images',  'SELECT, INSERT, UPDATE, DELETE'),
    ('tp_batch',   'tour_embeddings',    'SELECT, INSERT, UPDATE'),
    ('tp_batch',   'weather_forecast',   'SELECT, INSERT, UPDATE, DELETE'),
    ('tp_batch',   'schedule_places',    'SELECT'),
    ('tp_batch',   'batch_job_log',      'SELECT, INSERT, UPDATE'),
    ('tp_batch',   'api_call_quota',     'SELECT, INSERT, UPDATE'),
    ('tp_ai',      'region',             'SELECT'),
    ('tp_ai',      'tour_places',        'SELECT'),
    ('tp_ai',      'tour_place_details', 'SELECT'),
    ('tp_ai',      'tour_embeddings',    'SELECT'),
    ('tp_backend', 'region',             'SELECT'),
    ('tp_backend', 'tour_places',        'SELECT'),
    ('tp_backend', 'tour_place_details', 'SELECT'),
    ('tp_backend', 'tour_place_images',  'SELECT'),
    ('tp_backend', 'weather_forecast',   'SELECT'),
    ('tp_backend', 'users',              'SELECT, INSERT, UPDATE'),
    ('tp_backend', 'trips',              'SELECT, INSERT, UPDATE'),
    ('tp_backend', 'schedules',          'SELECT, INSERT, UPDATE, DELETE'),
    ('tp_backend', 'schedule_places',    'SELECT, INSERT, UPDATE, DELETE'),
    ('tp_backend', 'trip_shares',        'SELECT, INSERT, DELETE')
), roles(role) AS (
    VALUES ('tp_batch'), ('tp_ai'), ('tp_backend')
), tables AS (
    SELECT DISTINCT tbl FROM expected WHERE to_regclass('public.' || tbl) IS NOT NULL
), privs(priv) AS (
    VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')
), compared AS (
    SELECT r.role, t.tbl, p.priv,
           COALESCE(p.priv = ANY (string_to_array(replace(e.privs, ' ', ''), ',')), false) AS want,
           has_table_privilege(r.role, 'public.' || t.tbl, p.priv)                       AS have
    FROM roles r
    CROSS JOIN tables t
    CROSS JOIN privs p
    LEFT JOIN expected e ON e.role = r.role AND e.tbl = t.tbl
)
SELECT role AS "계정", tbl AS "테이블", priv AS "권한", want AS "있어야 함", have AS "실제"
FROM compared
WHERE want <> have
ORDER BY 1, 2, 3;

\echo
\echo '[4] 아직 없는 목표 테이블 — 마이그레이션으로 만든 뒤 03을 다시 실행'
SELECT t AS "테이블"
FROM unnest(ARRAY['region', 'tour_places', 'tour_place_details', 'tour_place_images',
                  'tour_embeddings', 'weather_forecast', 'users', 'trips', 'schedules',
                  'schedule_places', 'trip_shares', 'batch_job_log', 'api_call_quota']) AS t
WHERE to_regclass('public.' || t) IS NULL;

\echo
\echo '[5] INSERT 권한은 있는데 자동 증가 시퀀스를 못 쓰는 곳 — 비어 있어야 함'
SELECT r.role                AS "계정",
       c.relname             AS "테이블",
       s.oid::regclass::text AS "시퀀스"
FROM (VALUES ('tp_batch'), ('tp_ai'), ('tp_backend')) AS r(role)
JOIN pg_class c ON c.relnamespace = 'public'::regnamespace AND c.relkind = 'r'
JOIN pg_depend d ON d.refobjid = c.oid AND d.refclassid = 'pg_class'::regclass
                AND d.classid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
JOIN pg_class s ON s.oid = d.objid AND s.relkind = 'S'
WHERE has_table_privilege(r.role, c.oid, 'INSERT')
  AND NOT has_sequence_privilege(r.role, s.oid, 'USAGE')
ORDER BY 1, 2;

\echo
\echo '[6] 비밀번호를 정했는지 (슈퍼유저만 볼 수 있음. 오류가 나면 무시해도 됨)'
SELECT rolname AS "계정", rolpassword IS NOT NULL AS "비밀번호 있음"
FROM pg_authid
WHERE rolname IN ('tp_owner', 'tp_batch', 'tp_ai', 'tp_backend')
ORDER BY array_position(ARRAY['tp_owner', 'tp_batch', 'tp_ai', 'tp_backend'], rolname::text);

\echo
\echo '마지막으로 실제 로그인으로 확인:'
\echo '  psql -h <호스트> -U tp_ai -d <DB이름> -c "SHOW default_transaction_read_only"   -> on'
\echo '  psql -h <호스트> -U tp_batch -d <DB이름> -c "SELECT count(*) FROM users"          -> permission denied'
