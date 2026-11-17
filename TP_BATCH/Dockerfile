# syntax=docker/dockerfile:1
# TP_BATCH 이미지: 기본 실행은 상주 스케줄러 (python -m app.cli schedule, 매일 DAILY_CRON 시각에 daily)
# 다른 잡은 같은 이미지로 한 번만 실행한다. 예:
#   docker compose run --rm batch python -m app.cli status
#   docker compose run --rm batch python -m app.cli sync     # 임베딩 적재
# 빌드: docker build -t tp-batch ./TP_BATCH

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Seoul \
    HF_HOME=/cache/huggingface

WORKDIR /app

# sync(임베딩) 잡까지 돌릴 수 있게 requirements-embed.txt 를 쓴다. torch 는 CPU 전용.
COPY requirements.txt requirements-embed.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install -r requirements-embed.txt

COPY app app

RUN useradd --system --create-home app \
 && mkdir -p /cache/huggingface && chown -R app /cache
USER app

CMD ["python", "-m", "app.cli", "schedule"]
