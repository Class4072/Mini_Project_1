from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.travel_service import travel_service
from app.schemas.travel import (
    TravelSpotCreate,
    BulkTravelSpotCreate,
    TravelSpotResponse,
    TravelSpotListResponse,
    TravelRecommendRequest,
    TravelRecommendResponse,
    TravelSearchRequest,
)

router = APIRouter()


@router.post(
    "/recommend",
    response_model=TravelRecommendResponse,
    status_code=status.HTTP_200_OK,
    summary="여행 조건 기반 AI 맞춤 여행 플랜 추천 (지역/날짜/날씨/경로 포함)",
    description=(
        "사용자가 입력한 여행 조건(테마 질의어, 동행자, 선호지역, 날짜, 날씨 등)을 pgvector로 시맨틱 분석하여 "
        "최적의 지역, 일자별 일정, 날씨 브리핑, 그리고 최단 동선 이동 경로 안내를 제공합니다."
    ),
)
async def recommend_travel(
    req: TravelRecommendRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await travel_service.recommend_travel(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 추천 생성 중 오류 발생: {str(e)}",
        )


@router.post(
    "/search",
    summary="여행지 시맨틱/키워드 검색",
    description="자연어 질의 또는 키워드로 유사도가 높은 여행 스팟을 검색합니다.",
)
async def search_spots(
    req: TravelSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        results = await travel_service.search_spots(
            db=db,
            query=req.query,
            region=req.region,
            top_k=req.top_k,
            use_hybrid=req.use_hybrid,
        )
        return {
            "query": req.query,
            "region": req.region,
            "total_results": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행지 검색 중 오류 발생: {str(e)}",
        )


@router.post(
    "/spots",
    response_model=TravelSpotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="여행지 단건 등록 및 벡터화",
    description="새로운 여행 스팟을 등록하고 ko-sroberta 임베딩을 생성하여 pgvector에 저장합니다.",
)
async def create_spot(
    spot_in: TravelSpotCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await travel_service.create_spot(db, spot_in)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행지 등록 중 오류 발생: {str(e)}",
        )


@router.post(
    "/spots/bulk",
    response_model=List[TravelSpotResponse],
    status_code=status.HTTP_201_CREATED,
    summary="여행지 대량(Bulk) 일괄 등록 및 벡터화",
    description="여러 여행 스팟을 배치 단위로 일괄 등록하고 임베딩을 생성합니다.",
)
async def create_bulk_spots(
    bulk_in: BulkTravelSpotCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await travel_service.create_bulk_spots(db, bulk_in)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행지 대량 등록 중 오류 발생: {str(e)}",
        )


@router.get(
    "/spots",
    response_model=TravelSpotListResponse,
    summary="여행지 목록 및 필터링 조회",
    description="지역 또는 카테고리별로 등록된 여행지 목록을 페이징하여 조회합니다.",
)
async def list_spots(
    region: Optional[str] = Query(None, description="지역명 필터 (예: 강릉, 제주)"),
    category: Optional[str] = Query(None, description="카테고리 필터 (예: 카페, 자연)"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수"),
    db: AsyncSession = Depends(get_db),
):
    total, items = await travel_service.list_spots(
        db=db,
        region=region,
        category=category,
        skip=skip,
        limit=limit,
    )
    return TravelSpotListResponse(total=total, items=items)


@router.get(
    "/spots/{spot_id}",
    response_model=TravelSpotResponse,
    summary="여행지 단건 상세 조회",
)
async def get_spot(
    spot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    spot = await travel_service.get_spot(db, spot_id)
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 여행지를 찾을 수 없습니다.",
        )
    return spot


@router.delete(
    "/spots/{spot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="여행지 삭제",
)
async def delete_spot(
    spot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await travel_service.delete_spot(db, spot_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 여행지를 찾을 수 없습니다.",
        )
    return None
