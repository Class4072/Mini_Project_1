"""BT-010 날씨 예보 갱신: 기상청 단기예보 → tour_db.weather_forecast.

    python -m app.cli weather                       # 시도 16곳 (WEATHER_REGION_LEVEL)
    python -m app.cli weather --region PUSAN --dry-run

흐름
  1. region에서 격자(kma_nx, kma_ny)가 있는 지역을 고른다.
  2. 지역마다 가장 최근 발표분 단기예보를 받는다. 발표 직후라 아직 자료가 없으면 한 번 앞 발표분을 쓴다.
     격자가 같은 지역은 한 번만 부른다.
  3. 하루 한 줄로 합쳐(app.weather) 지역·날짜별로 덮어쓴다. 지역마다 커밋해서 한 곳이 실패해도 나머지는 남는다.
  4. WEATHER_KEEP_DAYS보다 오래된 예보를 지운다.
결과는 tour_db.batch_job_log에 job_id BT-010으로 남는다.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config import Settings
from app.db import try_job_lock
from app.kma import NO_DATA_CODE, KmaApiError, KmaClient, latest_base_time, previous_base_time
from app.quota import KST, DailyQuota, QuotaExhausted
from app.tour_db import (
    WeatherRegion,
    connect_tour_db,
    delete_forecasts_before,
    finish_job_log,
    load_weather_regions,
    start_job_log,
    upsert_forecasts,
)
from app.weather import DailyWeather, aggregate_daily

log = logging.getLogger(__name__)

JOB_ID = "BT-010"
LOCK_NAME = "tp_batch:weather"
SOURCE = "SHORT"


def run_weather(
    settings: Settings,
    region_codes: Optional[Sequence[str]] = None,
    level: Optional[str] = None,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(KST)
    level = (level or settings.weather_region_level).upper()

    with connect_tour_db(settings, readonly=dry_run) as conn:
        regions = load_weather_regions(conn, level, region_codes)
        if not regions:
            raise RuntimeError(
                "날씨를 받을 지역이 없습니다 (level={0}, region={1}). region의 kma_nx·kma_ny를 확인하세요.".format(
                    level, ",".join(region_codes or []) or "전체"
                )
            )
        if dry_run:
            client = KmaClient(settings.kma_base_url, settings.kma_service_key, settings.request_timeout_sec)
            try:
                return _dry_run(client, regions, now)
            finally:
                client.close()

        if not try_job_lock(conn, LOCK_NAME):
            log.warning("[weather] 다른 weather가 실행 중이라 건너뜁니다.")
            return {"skipped": "locked"}

        with connect_tour_db(settings) as quota_conn:
            quota = DailyQuota(quota_conn, settings.kma_daily_limit)
            client = KmaClient(
                settings.kma_base_url, settings.kma_service_key, settings.request_timeout_sec, quota=quota
            )
            log_id = start_job_log(conn, JOB_ID)
            try:
                stats = _update_all(conn, client, regions, now)
                stats["deleted"] = delete_forecasts_before(
                    conn, now.date() - timedelta(days=settings.weather_keep_days)
                )
                stats["calls"] = quota.used(client.service)
            except Exception as exc:
                conn.rollback()
                finish_job_log(conn, log_id, "FAILED", 0, len(regions), str(exc)[:2000])
                raise
            finally:
                client.close()

            finish_job_log(
                conn,
                log_id,
                stats["status"],
                stats["saved_rows"],
                len(stats["failed"]),
                "\n".join(stats["failed"])[:2000] or None,
            )
    log.info(
        "[weather] 종료 (%s) 지역 %s곳 중 %s곳 저장, %s행, 실패 %s곳, 지난 예보 %s행 삭제, 오늘 호출 %s회",
        stats["status"],
        len(regions),
        stats["saved_regions"],
        stats["saved_rows"],
        len(stats["failed"]),
        stats["deleted"],
        stats["calls"],
    )
    return stats


def _update_all(conn, client: KmaClient, regions: List[WeatherRegion], now: datetime) -> Dict[str, Any]:
    cache: Dict[Tuple[int, int], Tuple[datetime, List[DailyWeather]]] = {}
    saved_regions = 0
    saved_rows = 0
    failed: List[str] = []

    for index, region in enumerate(regions):
        try:
            base, days = _forecast_for(client, cache, region, now)
            saved_rows += upsert_forecasts(conn, region.region_code, days, SOURCE)
            conn.commit()
            saved_regions += 1
            log.info(
                "[weather] %s %s: %s일치 (발표 %s)",
                region.region_code,
                region.name,
                len(days),
                base.strftime("%m-%d %H시"),
            )
        except QuotaExhausted as exc:
            conn.rollback()
            log.warning("[weather] %s — 남은 %s곳은 다음 실행에 받습니다.", exc, len(regions) - index)
            failed.extend("{0}: 호출 한도".format(r.region_code) for r in regions[index:])
            break
        except Exception as exc:
            conn.rollback()
            log.warning("[weather] %s 실패: %s", region.region_code, exc)
            failed.append("{0}: {1}".format(region.region_code, exc))

    if not failed:
        status = "SUCCESS"
    elif saved_regions == 0:
        status = "FAILED"
    else:
        status = "PARTIAL"
    return {"status": status, "saved_regions": saved_regions, "saved_rows": saved_rows, "failed": failed}


def _forecast_for(
    client: KmaClient,
    cache: Dict[Tuple[int, int], Tuple[datetime, List[DailyWeather]]],
    region: WeatherRegion,
    now: datetime,
) -> Tuple[datetime, List[DailyWeather]]:
    grid = (region.nx, region.ny)
    if grid not in cache:
        base = latest_base_time(now)
        try:
            items = client.fetch_forecast(base, region.nx, region.ny)
        except KmaApiError as exc:
            if exc.result_code != NO_DATA_CODE:
                raise
            base = previous_base_time(base)
            items = client.fetch_forecast(base, region.nx, region.ny)
        days = aggregate_daily(items, now.date())
        if not days:
            raise RuntimeError("하루 날씨로 합칠 예보가 없습니다 (받은 항목 {0}건)".format(len(items)))
        cache[grid] = (base, days)
    return cache[grid]


def _dry_run(client: KmaClient, regions: List[WeatherRegion], now: datetime) -> Dict[str, Any]:
    """DB에 쓰지 않고 합친 결과만 출력한다 (키 확인용). 호출 수도 세지 않는다."""
    cache: Dict[Tuple[int, int], Tuple[datetime, List[DailyWeather]]] = {}
    failed: List[str] = []
    for region in regions:
        try:
            base, days = _forecast_for(client, cache, region, now)
        except QuotaExhausted:
            raise
        except Exception as exc:
            failed.append("{0}: {1}".format(region.region_code, exc))
            print("{0:<16} 실패: {1}".format(region.region_code, exc))
            continue
        print(
            "{0:<16} {1} (격자 {2},{3} / 발표 {4})".format(
                region.region_code, region.name, region.nx, region.ny, base.strftime("%m-%d %H시")
            )
        )
        for d in days:
            print(
                "    {0}  {1:<6} {2:>5}℃  강수확률 {3}%".format(
                    d.date,
                    d.condition,
                    "-" if d.temperature is None else "{0:.1f}".format(d.temperature),
                    "-" if d.precipitation_prob is None else d.precipitation_prob,
                )
            )
    return {"dry_run": True, "regions": len(regions), "failed": failed}
