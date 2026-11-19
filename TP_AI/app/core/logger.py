import sys
import os
from loguru import logger
from app.config import settings


def setup_logger():
    """애플리케이션 전역 로거를 초기화합니다. (AI.md 10.4 / 10.5 표준 로깅 규격)"""
    logger.remove()  # 기본 핸들러 제거

    # 콘솔 출력 포맷
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<magenta>[{extra[request_id]}]</magenta> - <level>{message}</level>"
    )

    log_level = "DEBUG" if settings.DEBUG else "INFO"

    # extra['request_id']가 없어도 깨지지 않도록 patcher 적용
    def default_request_id(record):
        if "request_id" not in record["extra"]:
            record["extra"]["request_id"] = "system"

    configured_logger = logger.patch(default_request_id)
    configured_logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True,
    )

    # 로그 디렉토리 생성 및 파일 로깅 (로테이션 및 보존 정책)
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    configured_logger.add(
        os.path.join(log_dir, "ai_service_{time:YYYY-MM-DD}.log"),
        rotation="500 MB",
        retention="14 days",
        level="INFO",
        serialize=True,  # JSON 포맷 로깅
        encoding="utf-8",
    )

    return configured_logger


app_logger = setup_logger()

