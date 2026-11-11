-- =============================================================
-- 02_lockdown_public.sql — 모든 계정에 열려 있는 기본 권한(PUBLIC) 회수 (DATABASE.md 6.3)
--
-- 슈퍼유저로 실행한다. 01 다음에 실행한다.
--
--   psql -h <호스트> -p <포트> -U <관리자> -d <DB이름> -f db/roles/02_lockdown_public.sql
--
-- PostgreSQL은 기본으로 모든 계정(PUBLIC)에 DB 접속과 public 스키마 사용을 허락한다.
-- 이걸 닫고, 01에서 직접 권한을 준 계정만 접속하게 한다.
--
-- 안전장치: 지금 PUBLIC 권한으로만 접속하고 있는 로그인 계정이 있으면 아무것도 바꾸지 않고 멈춘다.
-- (예: 공용 DB를 쓰는 다른 팀원 계정, 지금 코드가 쓰는 계정)
-- 계속 쓸 계정이면 먼저 권한을 직접 준 뒤 다시 실행한다.
--   GRANT CONNECT ON DATABASE <DB이름> TO <계정>;
--   GRANT USAGE ON SCHEMA public TO <계정>;
-- 새로 만든 DB라서 목록에 나온 계정이 이 DB를 쓸 일이 없다면, 막혀도 된다고 지정하고 실행한다.
--   psql ... -v allow_block=1 -f db/roles/02_lockdown_public.sql
--
-- 되돌리기 (관리자로 실행):
--   GRANT CONNECT, TEMPORARY ON DATABASE <DB이름> TO PUBLIC;
--   GRANT USAGE ON SCHEMA public TO PUBLIC;           -- PostgreSQL 15 이상의 기본값
--   (PostgreSQL 14 이하였다면: GRANT USAGE, CREATE ON SCHEMA public TO PUBLIC;)
-- =============================================================
\set ON_ERROR_STOP on

\if :{?allow_block}
\echo '안전장치를 건너뜁니다 (-v allow_block 지정). PUBLIC 권한으로만 쓰던 계정은 이 DB에 접속할 수 없게 됩니다.'
\else
-- 막힐 계정이 있는지 확인 (00_precheck.sql [2]와 같은 기준)
DO $$
DECLARE
    blocked text;
BEGIN
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
    SELECT string_agg(format('  - %s (%s)', rolname,
                             concat_ws(', ',
                                       CASE WHEN NOT has_connect THEN 'DB 접속' END,
                                       CASE WHEN NOT has_usage THEN 'public 스키마' END)),
                      E'\n' ORDER BY rolname)
    INTO blocked
    FROM login_roles
    WHERE NOT (has_connect AND has_usage);

    IF blocked IS NOT NULL THEN
        RAISE EXCEPTION E'아래 계정은 지금 PUBLIC 권한으로만 쓰고 있어서, 진행하면 막힙니다. 아무것도 바꾸지 않았습니다.\n%', blocked
            USING HINT = '계속 쓸 계정이면 권한을 직접 준 뒤 다시 실행하세요: '
                         'GRANT CONNECT ON DATABASE <DB이름> TO <계정>; GRANT USAGE ON SCHEMA public TO <계정>; '
                         '이 DB를 쓸 일이 없는 계정이면(새로 만든 DB 등) -v allow_block=1 을 붙여 다시 실행하세요.';
    END IF;
END $$;
\endif

REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

\echo
\echo '완료. 다음: 03_grant_tables.sql'
