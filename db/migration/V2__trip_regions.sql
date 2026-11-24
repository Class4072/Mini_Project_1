-- =============================================================
-- V2: 한 여행에 지역 여러 개 (DATABASE.md 4.14, 이슈 #14)
--
-- trips.region_code 는 대표 지역(요청의 첫 지역)으로 그대로 두고,
-- 고른 지역 전부를 순서대로 trip_regions 에 둔다.
-- =============================================================

-- 4.14 trip_regions — 여행 지역
CREATE TABLE trip_regions (
    trip_id     BIGINT      NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    sort_order  INTEGER     NOT NULL CHECK (sort_order BETWEEN 0 AND 4),  -- 요청 순서, 0 = 대표 지역 (최대 5곳)
    region_code VARCHAR(20) NOT NULL REFERENCES region (region_code),
    PRIMARY KEY (trip_id, sort_order),
    CONSTRAINT uk_trip_region UNIQUE (trip_id, region_code)
);

-- 이미 있는 여행은 대표 지역 하나로 채운다
INSERT INTO trip_regions (trip_id, sort_order, region_code)
SELECT id, 0, region_code FROM trips;

-- 6.4 권한: 여행 지역은 여행을 만들 때 같이 넣고 바꾸지 않는다
GRANT SELECT, INSERT ON trip_regions TO tp_backend;
