-- =============================================================
-- 00_precheck.sql — 실행 전 점검 (읽기만 한다. 아무것도 바꾸지 않는다)
--
--   psql -h <호스트> -p <포트> -U <관리자> -d <DB이름> -f db/roles/00_precheck.sql
--
-- 볼 것
--   [1] 접속한 관리자가 슈퍼유저인지 — 01~03은 슈퍼유저로 실행한다
--   [2] PUBLIC 기본 권한에 기대어 접속하는 계정 — 02를 실행하면 이 계정들은 막힌다.
--       목록이 비어 있지 않으면 계속 쓸 계정인지 정하고, 02 전에 권한을 직접 준다.
--   [3] tp_* 계정이 이미 있는지
--   [4] 목표 테이블(DATABASE.md 4장)이 있는지 — 없으면 03은 그 테이블을 건너뛴다
--   [5] pgvector 확장을 쓸 수 있는지
--   [6] public 스키마의 기존 테이블과 소유자 (참고)
-- =============================================================
\pset footer off

\echo
\echo '[1] 접속 정보'
SELECT current_database()                                           AS "DB",
       current_user                                                 AS "접속 계정",
       (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) AS "슈퍼유저",
       current_setting('server_version')                            AS "PostgreSQL";

\echo
\echo '[2] PUBLIC 권한에만 기대는 로그인 계정 — 02를 실행하면 막힘 (비어 있어야 안전)'
WITH db AS (
    SELECT datdba, COALESCE(datacl, acldefault('d', datdba)) AS acl
    FROM pg_database
    WHERE datname = current_database()
), sch AS (
    SELECT COALESCE(nspacl, acldefault('n', nspowner)) AS acl
    FROM pg_namespace
    WHERE nspname = 'public'
), login_roles AS (
    SELECT r.rolname,
           -- DB 소유자이거나, PUBLIC이 아닌 대상에게 준 CONNECT를 (자기 또는 소속 그룹으로) 받았는지
           r.oid = db.datdba OR EXISTS (
               SELECT 1 FROM aclexplode(db.acl) a
               WHERE a.privilege_type = 'CONNECT'
                 AND CASE WHEN a.grantee = 0 THEN false
                          ELSE pg_has_role(r.oid, a.grantee, 'USAGE') END
           ) AS has_connect,
           EXISTS (
               SELECT 1 FROM sch, aclexplode(sch.acl) a
               WHERE a.privilege_type = 'USAGE'
                 AND CASE WHEN a.grantee = 0 THEN false
                          ELSE pg_has_role(r.oid, a.grantee, 'USAGE') END
           ) AS has_usage
    FROM pg_roles r, db
    WHERE r.rolcanlogin
      AND NOT r.rolsuper
      AND r.rolname NOT LIKE 'pg\_%'
)
SELECT rolname         AS "계정",
       NOT has_connect AS "DB 접속이 막힘",
       NOT has_usage   AS "public 스키마가 막힘"
FROM login_roles
WHERE NOT (has_connect AND has_usage)
ORDER BY 1;

\echo
\echo '[3] 서비스 계정 (없으면 01에서 만든다)'
SELECT r.rolname     AS "계정",
       r.rolcanlogin AS "로그인",
       r.rolsuper    AS "슈퍼유저",
       COALESCE((SELECT array_to_string(s.setconfig, ', ')
                 FROM pg_db_role_setting s
                 WHERE s.setrole = r.oid AND s.setdatabase = 0), '') AS "계정 설정"
FROM pg_roles r
WHERE r.rolname IN ('tp_owner', 'tp_batch', 'tp_ai', 'tp_backend')
ORDER BY array_position(ARRAY['tp_owner', 'tp_batch', 'tp_ai', 'tp_backend'], r.rolname::text);

\echo
\echo '[4] 목표 테이블 (DATABASE.md 4장) — 없는 테이블은 03이 건너뛰고, 마이그레이션 뒤 03을 다시 실행'
SELECT u.t                          AS "테이블",
       c.oid IS NOT NULL            AS "있음",
       pg_get_userbyid(c.relowner)  AS "소유자"
FROM unnest(ARRAY['region', 'tour_places', 'tour_place_details', 'tour_place_images',
                  'tour_embeddings', 'weather_forecast', 'users', 'trips', 'schedules',
                  'schedule_places', 'trip_shares', 'batch_job_log', 'api_call_quota'])
     WITH ORDINALITY AS u(t, n)
LEFT JOIN pg_class c ON c.oid = to_regclass('public.' || u.t)
ORDER BY u.n;

\echo
\echo '[5] pgvector (행이 없으면 서버에 pgvector가 설치되어 있지 않음 → 01이 실패한다)'
SELECT name              AS "확장",
       default_version   AS "설치 가능 버전",
       installed_version AS "설치된 버전"
FROM pg_available_extensions
WHERE name = 'vector';

\echo
\echo '[6] public 스키마의 기존 테이블 소유자 (참고)'
SELECT pg_get_userbyid(relowner) AS "소유자",
       count(*)                  AS "테이블 수"
FROM pg_class
WHERE relnamespace = 'public'::regnamespace
  AND relkind IN ('r', 'p')
GROUP BY 1
ORDER BY 2 DESC;
