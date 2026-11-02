from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, init_db
from app.core.embedding import embedding_service
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize DB & pre-warm ML model on startup."""
    logger.info("Starting up FastAPI VectorStore application...")
    
    # 1. Warm up embedding model in background thread / on startup
    try:
        embedding_service.initialize()
    except Exception as e:
        logger.warning(f"Could not load embedding model at startup: {e}")

    # 2. Initialize DB schema (pgvector extension & tables)
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to connect or initialize database on startup: {e}")
        logger.warning("Please make sure your PostgreSQL with pgvector is running and DATABASE_URL in .env is correct.")

    yield

    logger.info("Shutting down application...")
    await engine.dispose()


app = FastAPI(
    title="AI Travel Recommendation & Route API",
    version="1.0.0",
    description="PostgreSQL pgvector + ko-sroberta 기반 여행 조건 분석, 지역/날씨 추천 및 이동 경로 최적화 안내 API",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="서버 상태 및 DB 연결, 임베딩 모델 로드 상태를 점검합니다.",
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

    return {
        "app_name": settings.APP_NAME,
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "embedding_model": {
            "name": settings.EMBEDDING_MODEL_NAME,
            "dimension": settings.EMBEDDING_DIMENSION,
            "status": model_status,
        },
    }
