-- =============================================================
-- 01_create_roles.sql — 서비스 계정 4개 만들기 (DATABASE.md 6.1, 6.3)
--
-- 슈퍼유저로 실행한다. 몇 번 실행해도 결과가 같다 (이미 있는 계정은 건너뜀).
--
--   psql -h <호스트> -p <포트> -U <관리자> -d <DB이름> -f db/roles/01_create_roles.sql
--
-- 비밀번호는 이 파일에 넣지 않는다. 실행한 뒤 계정마다 아래처럼 설정한다.
-- 입력이 화면에 보이지 않고, 서버에는 암호화된 값만 전달되어 셸 기록·서버 로그에 남지 않는다.
--
--   psql -h <호스트> -p <포트> -U <관리자> -d <DB이름> -c '\password tp_owner'
--   (tp_batch, tp_ai, tp_backend도 같은 방법으로)
--
-- 비밀번호를 정하기 전까지는 비밀번호 인증으로 로그인할 수 없다.
-- =============================================================
\set ON_ERROR_STOP on

-- pgvector: tour_embeddings가 쓴다. 확장은 관리자만 만들 수 있다.
CREATE EXTENSION IF NOT EXISTS vector;

-- 계정 만들기 (슈퍼유저·DB 생성·계정 생성 권한 없이)
DO $$
DECLARE
    r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['tp_owner', 'tp_batch', 'tp_ai', 'tp_backend'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            RAISE NOTICE '이미 있음: %', r;
        ELSE
            EXECUTE format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', r);
            RAISE NOTICE '만듦: %', r;
        END IF;
    END LOOP;
END $$;

-- AI 계정은 접속하면 항상 읽기 전용 트랜잭션 (실수로 쓰기를 시도해도 DB가 막는다)
ALTER ROLE tp_ai SET default_transaction_read_only = on;

-- 접속·스키마 권한. 테이블 권한은 03에서 준다.
-- tp_owner만 테이블을 만들 수 있다 (마이그레이션 전용).
GRANT CONNECT ON DATABASE :"DBNAME" TO tp_owner, tp_batch, tp_ai, tp_backend;
GRANT USAGE, CREATE ON SCHEMA public TO tp_owner;
GRANT USAGE         ON SCHEMA public TO tp_batch, tp_ai, tp_backend;

\echo
\echo '완료. 다음 순서:'
\echo '  1) 계정마다 비밀번호 설정:  psql ... -c ''\\password tp_owner''  (tp_batch, tp_ai, tp_backend도)'
\echo '  2) 00_precheck.sql [2]가 비어 있는지 확인한 뒤 02_lockdown_public.sql'
