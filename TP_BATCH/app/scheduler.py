"""B-08 스케줄러: 정해진 시각(한국 시간)에 잡을 돌린다.

    python -m app.cli schedule            # 포그라운드로 상주
    python -m app.cli schedule --run-now  # 띄우자마자 한 번씩 돌리고 이후 스케줄대로

등록하는 잡
  - daily   (DAILY_CRON, 기본 매일 04:00)       TourAPI 갱신 -> aidb
  - weather (WEATHER_CRON, 기본 3시간마다 정각) 기상청 단기예보 -> tour_db (BT-010)
            TOUR_DB_PASSWORD와 기상청 키가 있을 때만 올린다.

호출 한도는 한국 시간 자정에 초기화되므로, 새벽에 돌리면 하루치 한도를 온전히 쓴다.
상주 프로세스를 두기 어렵다면 cron/launchd에서 'python -m app.cli daily'를 불러도
똑같이 동작한다 (README 참고). 어느 쪽이든 겹쳐 실행되면 DB 잠금으로 한쪽만 돈다.
"""
import logging
from datetime import datetime

from app.config import Settings
from app.jobs.daily import run_daily
from app.jobs.weather import run_weather
from app.quota import KST

log = logging.getLogger(__name__)

TIMEZONE = "Asia/Seoul"


def _run_daily_safely(settings: Settings) -> None:
    # 예외가 스케줄러 밖으로 새면 다음 실행까지 막히지는 않지만 로그가 묻히므로 여기서 남긴다.
    try:
        run_daily(settings)
    except Exception:
        log.exception("[schedule] daily 실행 실패 — 다음 예정 시각에 다시 시도합니다.")


def _run_weather_safely(settings: Settings) -> None:
    try:
        run_weather(settings)
    except Exception:
        log.exception("[schedule] weather 실행 실패 — 다음 예정 시각에 다시 시도합니다.")


def run_scheduler(settings: Settings, run_now: bool = False) -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError as exc:
        raise RuntimeError(
            "APScheduler가 설치되어 있지 않습니다. 'pip install -r requirements.txt'를 실행하세요."
        ) from exc

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    trigger = CronTrigger.from_crontab(settings.daily_cron, timezone=TIMEZONE)
    scheduler.add_job(
        _run_daily_safely,
        trigger,
        args=[settings],
        id="daily",
        max_instances=1,
        coalesce=True,  # 맥이 잠들어 여러 번 놓쳤어도 깨어나면 한 번만 돈다
        misfire_grace_time=3 * 3600,
    )
    if run_now:
        scheduler.add_job(_run_daily_safely, args=[settings], id="daily-now", max_instances=1)

    next_run = trigger.get_next_fire_time(None, datetime.now(KST))
    log.info("[schedule] daily 등록: '%s' (다음 실행 %s)", settings.daily_cron, next_run)

    if settings.weather_ready:
        weather_trigger = CronTrigger.from_crontab(settings.weather_cron, timezone=TIMEZONE)
        scheduler.add_job(
            _run_weather_safely,
            weather_trigger,
            args=[settings],
            id="weather",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,  # 한 시간 넘게 밀렸으면 건너뛰고 다음 정각에 받는다
        )
        if run_now:
            scheduler.add_job(_run_weather_safely, args=[settings], id="weather-now", max_instances=1)
        log.info(
            "[schedule] weather 등록: '%s' (다음 실행 %s)",
            settings.weather_cron,
            weather_trigger.get_next_fire_time(None, datetime.now(KST)),
        )
    else:
        log.warning(
            "[schedule] weather 미등록: TOUR_DB_PASSWORD와 기상청 키(KMA_API_KEY 또는 KMA_API_AUTH_KEY)가 필요합니다."
        )
    log.info("[schedule] 시작. 종료는 Ctrl+C")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("[schedule] 종료")
