from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logger import app_logger
from app.api.deps import get_db
from app.services.ai_schedule_service import ai_schedule_service
from app.schemas.ai import (
    AIScheduleRequest,
    AIScheduleResponse,
    AIRescheduleRequest,
    AIRescheduleResponse,
)

router = APIRouter()


@router.post(
    "/schedule",
    response_model=AIScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="신규 맞춤형 여행 일정 생성 (AI.md 7.1)",
    description=(
        "백엔드로부터 여행 조건(지역, 날짜, 테마 등)과 당일 기상 예보 데이터를 전달받아, "
        "RAG(Vector DB) 시맨틱 검색 ➡️ 지리적 위경도 동선 최적화 ➡️ LLM 일정 빌드 3단계를 거쳐 "
        "환각 없는 완성형 여행 일정 JSON을 생성합니다."
    ),
)
async def generate_schedule(
    req: AIScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ai_schedule_service.generate_schedule(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        app_logger.exception(f"❌ [일정 생성 시스템 오류] {e}")
        error_detail = (
            f"일정 생성 중 시스템 오류가 발생했습니다: {str(e)}"
            if settings.DEBUG
            else "일정 생성 처리 중 시스템 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )


@router.post(
    "/reschedule",
    response_model=AIRescheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="기상 악화 대응 실시간 대체 일정 재추천 (AI.md 7.2)",
    description=(
        "여행 중 갑작스러운 기상 악화(우천/폭설 등) 발생 시, 현재 사용자의 위경도 좌표 기준 "
        "반경 내 실내 안전 명소를 즉각 추출하여 대체 동선을 재산출합니다."
    ),
)
async def reschedule(
    req: AIRescheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ai_schedule_service.reschedule(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        app_logger.exception(f"❌ [대체 일정 재추천 시스템 오류] {e}")
        error_detail = (
            f"대체 일정 재추천 중 시스템 오류가 발생했습니다: {str(e)}"
            if settings.DEBUG
            else "대체 일정 재추천 처리 중 시스템 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )

