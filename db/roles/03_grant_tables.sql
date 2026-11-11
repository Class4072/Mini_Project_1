-- =============================================================
-- 03_grant_tables.sql — 서비스 계정의 테이블 권한 (DATABASE.md 6.2, 6.4)
--
-- 슈퍼유저 또는 테이블 소유자(tp_owner)로 실행한다.
--
--   psql -h <호스트> -p <포트> -U <관리자> -d <DB이름> -f db/roles/03_grant_tables.sql
--
-- - 아래 표를 '정확히' 반영한다: 목표 테이블에서 서비스 계정 권한을 먼저 비우고 표대로 다시 준다.
--   그래서 몇 번 실행해도 결과가 같고, 표에 없는 권한은 남지 않는다.
-- - 아직 없는 테이블은 건너뛴다. 마이그레이션으로 테이블을 만든 뒤 다시 실행하면 채워진다.
-- - INSERT 권한을 받는 테이블은 자동 증가(BIGSERIAL) 시퀀스 권한도 같이 준다.
--   시퀀스는 테이블에서 찾아내므로 이름을 따로 적지 않는다.
-- - 권한을 바꿀 때는 DATABASE.md 6.2 표, 이 파일의 표, 04_verify.sql의 표를 같이 고친다.
-- =============================================================
\set ON_ERROR_STOP on

DO $$
DECLARE
    service_roles constant text := 'tp_batch, tp_ai, tp_backend';
    target_tables constant text[] := ARRAY[
        'region', 'tour_places', 'tour_place_details', 'tour_place_images',
        'tour_embeddings', 'weather_forecast', 'users', 'trips', 'schedules',
        'schedule_places', 'trip_shares', 'batch_job_log', 'api_call_quota'];
    t       text;
    g       record;
    seq     regclass;
    granted int    := 0;
    missing text[] := '{}';
BEGIN
    -- 1) 목표 테이블(과 그 시퀀스)에서 서비스 계정 권한 비우기
    FOREACH t IN ARRAY target_tables LOOP
        IF to_regclass('public.' || t) IS NULL THEN
            missing := missing || t;
            CONTINUE;
        END IF;
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %s', t, service_roles);
        FOR seq IN
            SELECT s.oid::regclass
            FROM pg_depend d
            JOIN pg_class s ON s.oid = d.objid AND s.relkind = 'S'
            WHERE d.classid = 'pg_class'::regclass
              AND d.refclassid = 'pg_class'::regclass
              AND d.refobjid = to_regclass('public.' || t)
              AND d.deptype IN ('a', 'i')          -- a: SERIAL/BIGSERIAL, i: IDENTITY
        LOOP
            EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM %s', seq, service_roles);
        END LOOP;
    END LOOP;

    -- 2) DATABASE.md 6.2 표대로 다시 주기
    FOR g IN
        SELECT * FROM (VALUES
            -- 배치: 장소·날씨·운영 테이블 쓰기. DELETE는 이미지·지난 예보 정리에만.
            ('tp_batch',   'region',             'SELECT, INSERT, UPDATE'),
            ('tp_batch',   'tour_places',        'SELECT, INSERT, UPDATE'),
            ('tp_batch',   'tour_place_details', 'SELECT, INSERT, UPDATE'),
            ('tp_batch',   'tour_place_images',  'SELECT, INSERT, UPDATE, DELETE'),
            ('tp_batch',   'tour_embeddings',    'SELECT, INSERT, UPDATE'),
            ('tp_batch',   'weather_forecast',   'SELECT, INSERT, UPDATE, DELETE'),
            ('tp_batch',   'schedule_places',    'SELECT'),                     -- BT-013 인기 장소 집계
            ('tp_batch',   'batch_job_log',      'SELECT, INSERT, UPDATE'),
            ('tp_batch',   'api_call_quota',     'SELECT, INSERT, UPDATE'),
            -- AI: 읽기 전용
            ('tp_ai',      'region',             'SELECT'),
            ('tp_ai',      'tour_places',        'SELECT'),
            ('tp_ai',      'tour_place_details', 'SELECT'),
            ('tp_ai',      'tour_embeddings',    'SELECT'),
            -- 백엔드: 회원·여행·일정 쓰기, 장소·날씨 읽기
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
        ) AS v(role, tbl, privs)
    LOOP
        CONTINUE WHEN to_regclass('public.' || g.tbl) IS NULL;

        EXECUTE format('GRANT %s ON TABLE public.%I TO %I', g.privs, g.tbl, g.role);
        granted := granted + 1;

        -- BIGSERIAL 컬럼에 INSERT하려면 시퀀스 권한이 따로 필요하다
        IF g.privs LIKE '%INSERT%' THEN
            FOR seq IN
                SELECT s.oid::regclass
                FROM pg_depend d
                JOIN pg_class s ON s.oid = d.objid AND s.relkind = 'S'
                WHERE d.classid = 'pg_class'::regclass
                  AND d.refclassid = 'pg_class'::regclass
                  AND d.refobjid = to_regclass('public.' || g.tbl)
                  AND d.deptype IN ('a', 'i')
            LOOP
                EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO %I', seq, g.role);
            END LOOP;
        END IF;
    END LOOP;

    RAISE NOTICE '권한 % 건 반영', granted;
    IF cardinality(missing) > 0 THEN
        RAISE NOTICE '아직 없는 테이블 % 개는 건너뜀 (마이그레이션 뒤 다시 실행): %',
            cardinality(missing), array_to_string(missing, ', ');
    END IF;
END $$;

\echo
\echo '완료. 다음: 04_verify.sql'
