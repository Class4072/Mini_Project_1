"""tour_db 접근 (DATABASE.md가 정한 공용 테이블).

다른 잡은 아직 aidb에 쓰지만, 공용 테이블은 tour_db에 tp_batch 계정으로 쓴다.
테이블은 백엔드 Flyway(db/migration)가 만들므로 여기서는 만들지 않는다.
"""
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Iterator, List, Optional, Sequence

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import execute_values

from app.config import Settings
from app.weather import DailyWeather

log = logging.getLogger(__name__)


@contextmanager
def connect_tour_db(settings: Settings, readonly: bool = False) -> Iterator[PgConnection]:
    conn = psycopg2.connect(
        host=settings.tour_db_host,
        port=settings.tour_db_port,
        dbname=settings.tour_db_name,
        user=settings.tour_db_user,
        password=settings.tour_db_password or None,
        connect_timeout=10,
        application_name="tp_batch",
    )
    try:
        if readonly:
            conn.set_session(readonly=True)
        yield conn
    finally:
        conn.close()


@dataclass(frozen=True)
class WeatherRegion:
    region_code: str
    name: str
    nx: int
    ny: int


def load_weather_regions(
    conn: PgConnection, level: str, region_codes: Optional[Sequence[str]] = None
) -> List[WeatherRegion]:
    """예보를 받을 지역. level=SIDO면 시도만, ALL이면 시군구까지. 격자가 없는 지역은 뺀다."""
    sql = "SELECT region_code, name, kma_nx, kma_ny FROM region WHERE kma_nx IS NOT NULL AND kma_ny IS NOT NULL"
    params: list = []
    if level != "ALL":
        sql += " AND level = %s"
        params.append(level)
    if region_codes:
        sql += " AND region_code = ANY(%s)"
        params.append(list(region_codes))
    sql += " ORDER BY region_code"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.commit()
    return [WeatherRegion(code, name, int(nx), int(ny)) for code, name, nx, ny in rows]


UPSERT_FORECAST_SQL = """
INSERT INTO weather_forecast
    (region_code, forecast_date, condition_code, temperature, precipitation_prob, source)
VALUES %s
ON CONFLICT (region_code, forecast_date) DO UPDATE SET
    condition_code     = EXCLUDED.condition_code,
    temperature        = EXCLUDED.temperature,
    precipitation_prob = EXCLUDED.precipitation_prob,
    source             = EXCLUDED.source,
    updated_at         = now()
"""


def upsert_forecasts(conn: PgConnection, region_code: str, days: Sequence[DailyWeather], source: str) -> int:
    """같은 지역·날짜가 있으면 새 예보로 덮어쓴다. 커밋은 호출하는 쪽이 한다."""
    rows = [(region_code, d.date, d.condition, d.temperature, d.precipitation_prob, source) for d in days]
    with conn.cursor() as cur:
        execute_values(cur, UPSERT_FORECAST_SQL, rows)
    return len(rows)


def delete_forecasts_before(conn: PgConnection, before: date) -> int:
    """지난 예보 정리. 일정에는 만들 때의 날씨가 복사돼 있어서 지난 예보는 쓰지 않는다."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM weather_forecast WHERE forecast_date < %s", (before,))
        deleted = cur.rowcount
    conn.commit()
    return deleted


def start_job_log(conn: PgConnection, job_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO batch_job_log (job_id, status) VALUES (%s, 'RUNNING') RETURNING id", (job_id,)
        )
        log_id = cur.fetchone()[0]
    conn.commit()
    return int(log_id)


def finish_job_log(
    conn: PgConnection,
    log_id: int,
    status: str,
    processed_count: int,
    failed_count: int,
    error_message: Optional[str],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE batch_job_log SET finished_at = now(), status = %s, processed_count = %s, "
            "failed_count = %s, error_message = %s WHERE id = %s",
            (status, processed_count, failed_count, error_message, log_id),
        )
    conn.commit()
