from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field


# --- TravelSpot Schemas ---

class TravelSpotCreate(BaseModel):
    name: str = Field(..., min_length=1, description="여행지/장소명 (예: 안목해변 커피거리)")
    region: str = Field(..., min_length=1, description="지역명 (예: 강원도 강릉시, 제주특별자치도 제주시)")
    address: Optional[str] = Field(None, description="상세 도로명 주소")
    category: str = Field(..., description="카테고리 (자연, 힐링, 카페, 액티비티, 맛집, 문화/역사, 실내 등)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="위도 (예: 37.7718)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="경도 (예: 128.9482)")
    description: str = Field(..., min_length=5, description="장소 상세 설명 및 분위기 (임베딩 텍스트 원본)")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="추가 메타데이터 (companion_types, best_seasons, weather_suitability, tags, estimated_stay_min 등)",
    )



class BulkTravelSpotCreate(BaseModel):
    spots: List[TravelSpotCreate] = Field(..., description="일괄 등록할 여행 스팟 목록")



class TravelSpotResponse(BaseModel):
    id: UUID
    name: str
    region: str
    address: Optional[str]
    category: str
    latitude: float
    longitude: float
    description: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TravelSpotListResponse(BaseModel):
    total: int
    items: List[TravelSpotResponse]


# --- Core Travel Recommendation Schemas (날짜, 인원, 지역 기반) ---

class TravelRecommendRequest(BaseModel):
    region: str = Field(..., min_length=1, description="여행 지역 (예: '강릉', '제주', '부산', '경주')")
    start_date: date = Field(..., description="여행 시작 날짜 (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="여행 종료 날짜 (YYYY-MM-DD, 미입력 시 당일치기 1일)")
    person_count: int = Field(2, ge=1, le=50, description="여행 인원 수 (예: 1명, 2명, 4명 등)")
    theme_or_keyword: Optional[str] = Field(
        None,
        description="추가 선호 테마나 키워드 (선택 사항, 예: '바다 뷰와 감성 카페', '아이와 함께 갈 실내 놀거리')",
    )
    spots_per_day: int = Field(3, ge=2, le=6, description="하루 권장 방문 스팟 수 (기본값: 3개)")


class RouteStep(BaseModel):
    order: int = Field(..., description="방문 순서 (1부터 시작)")
    spot_id: UUID
    name: str
    category: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    description: str
    stay_duration_min: int = Field(..., description="권장 체류 시간 (분)")
    distance_from_prev_km: float = Field(..., description="이전 스팟으로부터의 이동 거리 (km)")
    estimated_travel_min: int = Field(..., description="이전 스팟으로부터의 예상 이동 시간 (분)")
    tags: List[str] = Field(default_factory=list, description="장소 태그 목록")


class ItineraryDay(BaseModel):
    day: int = Field(..., description="일차 (Day 1, Day 2...)")
    date: str = Field(..., description="해당 일자의 실제 날짜 (YYYY-MM-DD)")
    title: str = Field(..., description="일자별 코스 타이틀")
    total_spots: int = Field(..., description="당일 방문 스팟 수")
    total_distance_km: float = Field(..., description="당일 총 이동 거리 (km)")
    total_travel_time_min: int = Field(..., description="당일 총 예상 이동 시간 (분)")
    routes: List[RouteStep] = Field(..., description="방문 스팟 순서 및 상세 이동 경로")


class DestinationSummary(BaseModel):
    requested_region: str = Field(..., description="요청된 여행 지역")
    theme: str = Field(..., description="여행 메인 테마")
    overview: str = Field(..., description="지역 및 추천 코스 개요")
    companion_group: str = Field(..., description="인원수에 맞춘 동행자 그룹 분류 (혼자/커플/가족/친구 등)")


class WeatherSummary(BaseModel):
    target_date: str = Field(..., description="기준 날짜")
    region: str = Field(..., description="지역")
    season: str = Field(..., description="계절")
    expected_weather: str = Field(..., description="예상 날씨 상태")
    expected_temperature: str = Field(..., description="예상 기온")
    travel_tip: str = Field(..., description="날씨에 맞춘 추천 복장 및 활동 팁")


class TravelRecommendResponse(BaseModel):
    request_summary: Dict[str, Any] = Field(..., description="입력받은 여행 조건 요약")
    destination_summary: DestinationSummary = Field(..., description="추천 지역 정보")
    weather_summary: WeatherSummary = Field(..., description="날짜에 맞는 날씨 분석 및 팁")
    itinerary: List[ItineraryDay] = Field(..., description="일자별 추천 놀거리/명소 및 최적 이동 경로")
    total_days: int = Field(..., description="총 여행 일수")
    total_spots_count: int = Field(..., description="총 추천 스팟 수")
    total_itinerary_distance_km: float = Field(..., description="전체 일정 총 이동 거리 (km)")


# --- Search Schemas ---

class TravelSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="검색할 키워드 또는 질의어")
    region: Optional[str] = Field(None, description="특정 지역 필터 (선택)")
    top_k: int = Field(10, ge=1, le=50, description="반환할 장소 수")
    use_hybrid: bool = Field(True, description="키워드 Trigram + 시맨틱 벡터 하이브리드 검색 여부")
