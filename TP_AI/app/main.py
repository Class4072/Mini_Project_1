from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, init_db
from app.core.embedding import embedding_service
from app.core.llm_client import llm_client
from app.api.v1.router import api_router
from app.core.logger import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize DB & pre-warm ML model on startup."""
    app_logger.info("Starting up FastAPI AI Travel Service...")
    
    # 1. Warm up embedding model in background thread / on startup
    try:
        embedding_service.initialize()
    except Exception as e:
        app_logger.warning(f"Could not load embedding model at startup: {e}")

    # 2. Initialize DB schema (pgvector extension & tables)
    try:
        await init_db()
    except Exception as e:
        app_logger.error(f"Failed to connect or initialize database on startup: {e}")
        app_logger.warning("Please make sure your PostgreSQL with pgvector is running and DATABASE_URL in .env is correct.")

    yield

    app_logger.info("Shutting down application...")
    await llm_client.close()
    await engine.dispose()


app = FastAPI(
    title="AI Travel Recommendation & Route API",
    version="1.0.0",
    description="PostgreSQL pgvector + ko-sroberta 기반 여행 조건 분석, 지역/날씨 추천 및 이동 경로 최적화 안내 API",
    lifespan=lifespan,
)

# CORS Middleware (보안 설정: 와일드카드 origin 사용 시 credentials 비활성화)
is_wildcard = "*" in settings.CORS_ORIGINS
if is_wildcard and settings.APP_ENV == "production":
    app_logger.warning("🚨 [보안 경고] 프로덕션 환경에서 CORS 와일드카드('*')가 활성화되어 있습니다. 도메인 화이트리스트 지정을 권장합니다.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# 보안 및 안정성을 위한 전역 예외 핸들러 (CWE-209 민감 정보 노출 방지)
# -----------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 파라미터 유효성 검증 실패 핸들러"""
    app_logger.warning(f"⚠️ [입력 검증 실패] {request.method} {request.url.path} | errors={exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "요청 파라미터 유효성 검증에 실패했습니다.",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """비즈니스 로직 값 오류 핸들러"""
    app_logger.warning(f"⚠️ [비즈니스 검증 오류] {request.method} {request.url.path} | {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": str(exc),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """예기치 않은 시스템 예외 핸들러 (민감 스택 트레이스 은폐)"""
    app_logger.exception(f"❌ [서버 내부 예외 발생] {request.method} {request.url.path} | {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "서버 내부 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )


# Include API v1 Router
app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="서버 상태 및 DB 연결, 임베딩 모델, LLM Provider 진단 상태를 점검합니다.",
)
async def health_check():
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
            db_status = "connected"
    except Exception as e:
        db_status = f"disconnected ({str(e)})"

    model_status = "loaded" if embedding_service._model is not None else "not loaded"

    # API Key 마스킹 (AI.md 10.4 보안 규격)
    def mask_key(k: str | None) -> str:
        if not k:
            return "not_configured"
        return f"{k[:4]}****" if len(k) > 4 else "****"

    llm_info = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL_NAME,
        "endpoint": settings.OLLAMA_BASE_URL if settings.LLM_PROVIDER == "ollama" else "cloud_api",
        "key_status": mask_key(settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.GEMINI_API_KEY),
    }

    return {
        "app_name": settings.APP_NAME,
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "embedding_model": {
            "name": settings.EMBEDDING_MODEL_NAME,
            "dimension": settings.EMBEDDING_DIMENSION,
            "status": model_status,
        },
        "llm_engine": llm_info,
    }

