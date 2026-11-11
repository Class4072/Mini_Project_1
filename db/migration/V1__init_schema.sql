-- =============================================================
-- V1__init_schema.sql — TP 통합 스키마 (DATABASE.md 4장 DDL + 6.4 테이블 권한)
--
-- 백엔드 Flyway가 tp_owner 계정으로 실행한다 (DATABASE.md 팀 합의 5번 제안).
-- 먼저 DB 관리자가 db/roles/01_create_roles.sql 로 계정과 pgvector 확장을 준비해 둬야 한다.
-- (tp_owner는 확장을 만들 수 없고, GRANT 대상 계정이 없으면 이 파일이 실패한다)
--
-- 이미 적용된 마이그레이션 파일은 고치지 않는다. 바꿀 내용은 V2__... 로 새로 만든다.
-- =============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 4.1 region — 지역 마스터
CREATE TABLE region (
    region_code       VARCHAR(20)  PRIMARY KEY,             -- 예: PUSAN, GANGWON, GANGNEUNG
    name              VARCHAR(50)  NOT NULL,                -- 예: 부산광역시, 강릉시
    level             VARCHAR(10)  NOT NULL CHECK (level IN ('SIDO', 'SIGUNGU')),
    parent_code       VARCHAR(20)  REFERENCES region (region_code),  -- 시군구 → 상위 시도
    tour_area_code    VARCHAR(10),                          -- TourAPI areaCode
    tour_sigungu_code VARCHAR(10),                          -- TourAPI sigunguCode
    ldong_regn_cd     VARCHAR(10),                          -- TourAPI 법정동 시도 코드 (KorService2)
    ldong_signgu_cd   VARCHAR(10),                          -- TourAPI 법정동 시군구 코드 (KorService2)
    kma_nx            INTEGER,                              -- 기상청 단기예보 격자 X (대표 지점)
    kma_ny            INTEGER,                              -- 기상청 단기예보 격자 Y
    kma_mid_reg_id    VARCHAR(10),                          -- 기상청 중기예보 구역코드
    latitude          DOUBLE PRECISION,                     -- 대표 좌표 (격자 변환, 지도 중심)
    longitude         DOUBLE PRECISION
);

-- 4.2 tour_places — 장소
CREATE TABLE tour_places (
    id                 BIGSERIAL    PRIMARY KEY,
    content_id         VARCHAR(50)  NOT NULL UNIQUE,        -- TourAPI contentid
    content_type_id    VARCHAR(10)  NOT NULL,               -- 12, 14, 15, 28, 32, 38, 39
    name               VARCHAR(255) NOT NULL,
    category           VARCHAR(20)  NOT NULL CHECK (category IN (
                           'TOUR_SPOT', 'CULTURE', 'FESTIVAL', 'LEISURE',
                           'ACCOMMODATION', 'SHOPPING', 'RESTAURANT', 'CAFE')),
    region_code        VARCHAR(20)  NOT NULL REFERENCES region (region_code),  -- 시군구 단위
    address            VARCHAR(255),
    latitude           DOUBLE PRECISION NOT NULL,           -- TourAPI mapy
    longitude          DOUBLE PRECISION NOT NULL,           -- TourAPI mapx
    image_url          VARCHAR(1000),                       -- 대표 이미지 (firstimage)
    is_indoor          BOOLEAN      NOT NULL DEFAULT FALSE, -- BT-011 실내 여부
    suitable_weathers  VARCHAR(10)[] NOT NULL DEFAULT '{}', -- BT-011, WeatherCondition 값
    suitable_seasons   VARCHAR(10)[] NOT NULL DEFAULT '{}', -- BT-011, Season 값 (비어 있으면 사계절)
    source_modified_at TIMESTAMPTZ,                         -- TourAPI modifiedtime (증분 동기화 기준)
    is_deleted         BOOLEAN      NOT NULL DEFAULT FALSE, -- BT-009
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX ix_tour_places_region   ON tour_places (region_code) WHERE is_deleted = FALSE;
CREATE INDEX ix_tour_places_category ON tour_places (category);

-- 4.3 tour_place_details — 상세정보
CREATE TABLE tour_place_details (
    place_id           BIGINT       PRIMARY KEY REFERENCES tour_places (id) ON DELETE CASCADE,
    overview           TEXT,                                -- 개요 (임베딩 텍스트의 본문)
    business_hours     TEXT,                                -- 운영시간 원문
    holiday_info       TEXT,                                -- 휴무일 원문
    open_time          TIME,                                -- 대표 개장 시각 (해석 못 하면 NULL)
    close_time         TIME,                                -- 대표 폐장 시각 (open_time보다 작으면 다음 날)
    closed_weekdays    VARCHAR(3)[] NOT NULL DEFAULT '{}',  -- 매주 쉬는 요일: MON ~ SUN
    closed_on_holidays BOOLEAN      NOT NULL DEFAULT FALSE, -- 공휴일 휴무
    parking_info       TEXT,                                -- 주차 원문
    main_menu          VARCHAR(255),                        -- 음식점 대표메뉴 (BT-003)
    event_start_date   DATE,                                -- 축제 시작일 (BT-005)
    event_end_date     DATE,                                -- 축제 종료일
    fetched_at         TIMESTAMPTZ  NOT NULL DEFAULT now(), -- 상세 API를 조회한 시각
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- 4.4 tour_place_images — 이미지
CREATE TABLE tour_place_images (
    id            BIGSERIAL     PRIMARY KEY,
    place_id      BIGINT        NOT NULL REFERENCES tour_places (id) ON DELETE CASCADE,
    image_url     VARCHAR(1000) NOT NULL,
    thumbnail_url VARCHAR(1000),
    is_valid      BOOLEAN       NOT NULL DEFAULT TRUE,      -- BT-008 URL 유효성 검증 결과
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (place_id, image_url)
);

-- 4.5 tour_embeddings — RAG 벡터
CREATE TABLE tour_embeddings (
    place_id    BIGINT       PRIMARY KEY REFERENCES tour_places (id) ON DELETE CASCADE,
    chunk_text  TEXT         NOT NULL,                      -- 임베딩에 쓴 텍스트 (BATCH.md 4.1 템플릿)
    embedding   vector(1536) NOT NULL,
    model_name  VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_tour_embeddings_hnsw
    ON tour_embeddings USING hnsw (embedding vector_cosine_ops);

-- 4.6 weather_forecast — 날씨 예보
CREATE TABLE weather_forecast (
    id                 BIGSERIAL   PRIMARY KEY,
    region_code        VARCHAR(20) NOT NULL REFERENCES region (region_code),
    forecast_date      DATE        NOT NULL,
    condition_code     VARCHAR(10) NOT NULL CHECK (condition_code IN ('SUNNY', 'CLOUDY', 'RAIN', 'SNOW')),
    temperature        DOUBLE PRECISION,                    -- 대표 기온 (℃)
    precipitation_prob INTEGER,                             -- 강수확률 (%)
    source             VARCHAR(10) NOT NULL CHECK (source IN ('SHORT', 'MID')),  -- 단기 / 중기예보
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uk_region_date UNIQUE (region_code, forecast_date)
);

-- 4.7 users — 회원
CREATE TABLE users (
    id          BIGSERIAL    PRIMARY KEY,
    email       VARCHAR(255) NOT NULL UNIQUE,
    nickname    VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

-- 4.8 trips — 여행 (요청 필드는 FE·AI 일정 생성 요청 초안 기준)
CREATE TABLE trips (
    id               BIGSERIAL     PRIMARY KEY,
    user_id          BIGINT        REFERENCES users (id),   -- 로그인 범위가 정해지면 NOT NULL 여부 결정
    title            VARCHAR(100),                          -- AI tripName (생성 완료 후 채움)
    region_code      VARCHAR(20)   NOT NULL REFERENCES region (region_code),
    start_date       DATE          NOT NULL,
    end_date         DATE          NOT NULL,
    companion_type   VARCHAR(30)   NOT NULL CHECK (companion_type IN (
                         'SOLO', 'COUPLE', 'FRIENDS', 'FAMILY_WITH_KIDS', 'FAMILY_WITH_PARENTS', 'GROUP')),
    traveler_count   SMALLINT      NOT NULL DEFAULT 1 CHECK (traveler_count BETWEEN 1 AND 100),
    transport        VARCHAR(20)   NOT NULL CHECK (transport IN ('CAR', 'PUBLIC_TRANSIT', 'WALK')),
    themes           VARCHAR(20)[] NOT NULL DEFAULT '{}'    -- 0~3개, 비어 있으면 '골고루'
                         CHECK (cardinality(themes) <= 3
                            AND themes <@ ARRAY['NATURE', 'HISTORY_CULTURE', 'FOOD', 'CAFE',
                                                'ACTIVITY', 'SHOPPING', 'FESTIVAL', 'HEALING']::VARCHAR(20)[]),
    places_per_day   VARCHAR(10)   NOT NULL DEFAULT 'NORMAL' CHECK (places_per_day IN ('RELAXED', 'NORMAL', 'PACKED')),
    start_time       VARCHAR(10)   NOT NULL DEFAULT 'NORMAL' CHECK (start_time IN ('EARLY', 'NORMAL', 'LATE')),
    weather_summary  TEXT,                                  -- AI weatherSummary
    memo             TEXT,                                  -- TR-003 메모
    status           VARCHAR(20)   NOT NULL DEFAULT 'GENERATING'
                         CHECK (status IN ('GENERATING', 'COMPLETED', 'FAILED')),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,                           -- TR-004 Soft Delete
    CONSTRAINT ck_trip_period CHECK (end_date >= start_date AND end_date - start_date <= 13)  -- 최대 14일 (AI 상한)
);

CREATE INDEX ix_trips_user ON trips (user_id) WHERE deleted_at IS NULL;

-- 4.9 schedules — 일자별 일정
CREATE TABLE schedules (
    id                 BIGSERIAL   PRIMARY KEY,
    trip_id            BIGINT      NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    day_number         SMALLINT    NOT NULL,                -- 1일차, 2일차 …
    schedule_date      DATE        NOT NULL,
    weather_condition  VARCHAR(10) CHECK (weather_condition IN ('SUNNY', 'CLOUDY', 'RAIN', 'SNOW')),
    temperature        DOUBLE PRECISION,                    -- 일자 탭 표시용 (예: "비 16℃")
    precipitation_prob INTEGER,
    UNIQUE (trip_id, day_number)
);

-- 4.10 schedule_places — 방문 장소
CREATE TABLE schedule_places (
    id           BIGSERIAL PRIMARY KEY,
    schedule_id  BIGINT    NOT NULL REFERENCES schedules (id) ON DELETE CASCADE,
    place_id     BIGINT    NOT NULL REFERENCES tour_places (id),
    visit_order  SMALLINT  NOT NULL,                        -- AI step
    start_time   TIME,
    end_time     TIME,
    reason       TEXT,                                      -- AI 추천 사유 · 날씨 팁 (화면 말풍선)
    UNIQUE (schedule_id, visit_order)
);

-- 4.11 trip_shares — 공유 링크
CREATE TABLE trip_shares (
    id          BIGSERIAL   PRIMARY KEY,
    trip_id     BIGINT      NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    token       VARCHAR(64) NOT NULL UNIQUE,                -- 공유 URL: https://trp.com/s/{token}
    expires_at  TIMESTAMPTZ,                                -- NULL이면 만료 없음
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4.12 batch_job_log — 배치 실행 이력
CREATE TABLE batch_job_log (
    id              BIGSERIAL   PRIMARY KEY,
    job_id          VARCHAR(10) NOT NULL,                   -- BT-001 ~ BT-013
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(10) NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED')),
    processed_count INTEGER     NOT NULL DEFAULT 0,
    failed_count    INTEGER     NOT NULL DEFAULT 0,
    error_message   TEXT
);

-- 4.13 api_call_quota — 외부 API 일일 호출 수
CREATE TABLE api_call_quota (
    usage_date  DATE        NOT NULL,                       -- 한국 시간 기준 (한도가 KST 자정에 초기화)
    service     VARCHAR(50) NOT NULL,                       -- 예: KorService2, VilageFcstInfoService_2.0
    calls       INTEGER     NOT NULL DEFAULT 0,
    PRIMARY KEY (usage_date, service)
);

-- 6.4 테이블 권한 (db/roles/03_grant_tables.sql 과 같은 표)
-- 배치
GRANT SELECT, INSERT, UPDATE
    ON region, tour_places, tour_place_details, tour_embeddings, batch_job_log, api_call_quota
    TO tp_batch;
GRANT SELECT, INSERT, UPDATE, DELETE ON tour_place_images, weather_forecast TO tp_batch;
GRANT SELECT ON schedule_places TO tp_batch;                    -- BT-013 인기 장소 집계
GRANT USAGE, SELECT ON SEQUENCE
    tour_places_id_seq, tour_place_images_id_seq, weather_forecast_id_seq, batch_job_log_id_seq
    TO tp_batch;

-- AI (읽기 전용)
GRANT SELECT ON region, tour_places, tour_place_details, tour_embeddings TO tp_ai;

-- 백엔드
GRANT SELECT ON region, tour_places, tour_place_details, tour_place_images, weather_forecast TO tp_backend;
GRANT SELECT, INSERT, UPDATE         ON users, trips              TO tp_backend;
GRANT SELECT, INSERT, UPDATE, DELETE ON schedules, schedule_places TO tp_backend;
GRANT SELECT, INSERT, DELETE         ON trip_shares               TO tp_backend;
GRANT USAGE, SELECT ON SEQUENCE
    users_id_seq, trips_id_seq, schedules_id_seq, schedule_places_id_seq, trip_shares_id_seq
    TO tp_backend;
