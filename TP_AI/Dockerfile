# syntax=docker/dockerfile:1
# TP_AI 이미지: FastAPI(uvicorn) + CPU 전용 torch (임베딩)
# LLM(Ollama)은 컨테이너 밖(맥미니 호스트)에서 돌고, OLLAMA_BASE_URL 로 호출한다.
# 빌드: docker build -t tp-ai ./TP_AI

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Seoul \
    HF_HOME=/cache/huggingface

WORKDIR /app

# torch 는 CPU 전용 빌드를 먼저 설치한다 (기본 PyPI 빌드는 CUDA 포함이라 수 GB)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install -r requirements.txt

COPY app app

# 임베딩 모델 캐시(HF_HOME)는 볼륨으로 붙인다. 볼륨이 이 소유권을 이어받도록 미리 만들어 둔다.
RUN useradd --system --create-home app \
 && mkdir -p /cache/huggingface && chown -R app /cache
RUN mkdir -p /app/logs && chown app:app /app/logs
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
