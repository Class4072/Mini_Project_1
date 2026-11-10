import datetime
from typing import List, Optional, Union, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ==============================================================================
# 1. 신규 여행 일정 생성 DTO (02_요청 데이터 명세 초안.md & AI.md)
# ==============================================================================

class DailyWeatherInput(BaseModel):
    """일자별 기상 예보 데이터"""
    date: datetime.date = Field(..., description="예보 날짜 (YYYY-MM-DD)")
    condition: str = Field(..., description="날씨 상태 (예: RAIN, SUNNY, CLOUDY, SNOW)")
    temp: Optional[float] = Field(None, description="예상 평균 기온 (℃)")
    precipitationProbability: Optional[int] = Field(None, description="강수 확률 (%)")


class AIScheduleRequest(BaseModel):
    """일정 생성 요청 DTO (02_요청 데이터 명세 초안 규격 및 백엔드 확장 완벽 지원)"""
    
    # 02_요청 데이터 명세 초안 필드
    regionCodes: Optional[List[str]] = Field(
        None,
        description="지역 코드 배열 (TourAPI 지역코드 1:서울, 6:부산, 39:제주 등 또는 한글명)",
    )
    startDate: datetime.date = Field(..., description="여행 시작일 (YYYY-MM-DD)")
    endDate: datetime.date = Field(..., description="여행 종료일 (YYYY-MM-DD)")
    companionType: Optional[str] = Field(
        "FRIENDS",
        description="동행 유형 코드 (SOLO, COUPLE, FRIENDS, FAMILY_WITH_KIDS, FAMILY_WITH_PARENTS, GROUP)",
    )
    travelerCount: Optional[int] = Field(
        2,
        ge=1,
        le=100,
        description="여행 인원 수 (혼자=1, 그 외 2 이상, 최대 100명)",
    )
    transport: Optional[str] = Field(
        "PUBLIC_TRANSIT",
        description="이동 수단 코드 (CAR, PUBLIC_TRANSIT, WALK)",
    )
    themes: Optional[List[str]] = Field(
        default_factory=list,
        description="취향 테마 코드 배열 (NATURE, HISTORY_CULTURE, FOOD, CAFE, ACTIVITY, SHOPPING, FESTIVAL, HEALING 등)",
    )
    placesPerDay: Optional[str] = Field(
        "NORMAL",
        description="하루 방문 장소 수 (RELAXED: 2~3곳, NORMAL: 4~5곳, PACKED: 6곳 이상)",
    )
    startTime: Optional[str] = Field(
        "NORMAL",
        description="첫 일정 시작 시간 코드 (EARLY: 08:00, NORMAL: 10:00, LATE: 11:00)",
    )

    # 백엔드 연동 확장 필드 (하위 호환성 및 날씨 정보 주입)
    regionCode: Optional[str] = Field(
        None,
        description="단일 지역명 또는 코드 (호환용)",
    )
    theme: Optional[str] = Field(
        None,
        description="단일 테마 문자열 (호환용)",
    )
    transportation: Optional[str] = Field(
        None,
        description="이동 수단 문자열 (호환용)",
    )
    personCount: Optional[int] = Field(
        None,
        description="인원 수 (호환용)",
    )
    dailyWeathers: Optional[List[DailyWeatherInput]] = Field(
        default_factory=list,
        description="백엔드에서 사전 조회한 일자별 기상 예보 데이터 (없으면 AI가 자동 계절/날씨 추론)",
    )

    @model_validator(mode="before")
    @classmethod
    def reconcile_legacy_and_draft_fields(cls, data: Any) -> Any:
        """02_요청 데이터 명세 초안 필드와 기존 필드 간의 상호 호환 정규화"""
        if not isinstance(data, dict):
            return data

        # 1. regionCodes <-> regionCode 상호 보완
        if not data.get("regionCodes") and data.get("regionCode"):
            data["regionCodes"] = [data["regionCode"]]
        elif data.get("regionCodes") and not data.get("regionCode"):
            data["regionCode"] = data["regionCodes"][0]

        # 2. travelerCount <-> personCount 상호 보완
        if data.get("travelerCount") and not data.get("personCount"):
            data["personCount"] = data["travelerCount"]
        elif data.get("personCount") and not data.get("travelerCount"):
            data["travelerCount"] = data["personCount"]

        # 3. transport <-> transportation 상호 보완
        if data.get("transport") and not data.get("transportation"):
            data["transportation"] = data["transport"]
        elif data.get("transportation") and not data.get("transport"):
            data["transport"] = data["transportation"]

        # 4. themes <-> theme 상호 보완
        if data.get("themes") and not data.get("theme"):
            data["theme"] = ", ".join(data["themes"])
        elif data.get("theme") and not data.get("themes"):
            data["themes"] = [data["theme"]]

        return data

    @model_validator(mode="after")
    def validate_date_range(self) -> "AIScheduleRequest":
        """여행 시작일과 종료일 순서 및 범위 무결성 검증 (CWE-400 자원 고갈 방어)"""
        if self.endDate < self.startDate:
            raise ValueError(
                f"여행 종료일(endDate: {self.endDate})은 시작일(startDate: {self.startDate})과 같거나 이후여야 합니다."
            )
        
        travel_days = (self.endDate - self.startDate).days + 1
        if travel_days > 14:
            raise ValueError(
                f"지원 가능한 최대 여행 기간은 14일(2주)입니다. (요청된 기간: {travel_days}일)"
            )

        if self.regionCodes and len(self.regionCodes) > 5:
            raise ValueError(
                f"연계 가능한 여행 지역은 최대 5개까지입니다. (요청된 지역 수: {len(self.regionCodes)}개)"
            )

        return self


    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "regionCodes": ["6"],
                "startDate": "2026-11-01",
                "endDate": "2026-11-03",
                "companionType": "FRIENDS",
                "travelerCount": 3,
                "transport": "PUBLIC_TRANSIT",
                "themes": ["FOOD", "NATURE"],
                "placesPerDay": "NORMAL",
                "startTime": "NORMAL",
            }
        }
    )


class MapBounds(BaseModel):
    """지도 화면 영역 (카카오맵 fitBounds용)"""
    minLatitude: float = Field(..., description="최소 위도 (남단)")
    maxLatitude: float = Field(..., description="최대 위도 (북단)")
    minLongitude: float = Field(..., description="최소 경도 (서단)")
    maxLongitude: float = Field(..., description="최대 경도 (동단)")


class MapViewport(BaseModel):
    """카카오맵 초기 중심점 및 뷰포트 영역 메타데이터"""
    centerLatitude: float = Field(..., description="중심 위도")
    centerLongitude: float = Field(..., description="중심 경도")
    bounds: MapBounds = Field(..., description="전체 마커를 포함하는 경계 박스")


class AISchedulePlace(BaseModel):
    """일정 내 단일 방문 장소 DTO"""
    step: int = Field(..., description="방문 순서 (1부터 시작)")
    placeId: Union[str, int, UUID] = Field(..., description="장소 고유 ID")
    placeName: str = Field(..., description="장소명")
    category: str = Field(..., description="장소 카테고리")
    startTime: str = Field(..., description="방문 시작 시각 (HH:MM)")
    endTime: str = Field(..., description="방문 종료 시각 (HH:MM)")
    stayTimeMinutes: int = Field(..., description="체류 시간 (분)")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    reason: str = Field(..., description="AI 추천 사유 (날씨/테마 연계 팁 포함)")
    address: Optional[str] = Field(None, description="장소 주소")
    distanceFromPrevKm: Optional[float] = Field(None, description="직전 장소로부터의 이동 거리 (km)")
    estimatedTravelMinutes: Optional[int] = Field(None, description="직전 장소로부터의 예상 이동 시간 (분)")
    transportMode: Optional[str] = Field(None, description="이동 수단 (CAR, PUBLIC_TRANSIT, WALK)")


class AIDailySchedule(BaseModel):
    """일자별 여행 일정 DTO"""
    day: int = Field(..., description="여행 일차 (Day 1, Day 2...)")
    date: str = Field(..., description="해당 일자 (YYYY-MM-DD)")
    weatherCondition: str = Field(..., description="해당 일자의 날씨 상태")
    mapViewport: Optional[MapViewport] = Field(None, description="해당 일차의 카카오맵 중심 좌표 및 뷰포트 영역")
    totalDayDistanceKm: Optional[float] = Field(None, description="해당 일차 총 이동 거리 (km)")
    totalDayTravelMinutes: Optional[int] = Field(None, description="해당 일차 총 이동 시간 (분)")
    places: List[AISchedulePlace] = Field(default_factory=list, description="방문 장소 순서 목록")



class AIScheduleResponse(BaseModel):
    """완성형 여행 일정 JSON 응답 (AI.md 5.1 규격)"""
    tripName: str = Field(..., description="일정 전체 타이틀")
    weatherSummary: str = Field(..., description="날씨 및 코스 구성 총평")
    dailySchedules: List[AIDailySchedule] = Field(..., description="일자별 상세 일정 목록")


# ==============================================================================
# 2. 실시간 대체 일정 재추천 DTO (AI.md 7.2 & 8장)
# ==============================================================================

class AIRescheduleRequest(BaseModel):
    """기상 악화 대응 실시간 대체 일정 재추천 요청 DTO"""
    regionCode: str = Field(..., description="지역명 또는 코드")
    currentLatitude: float = Field(..., description="여행자의 현재 위치 위도")
    currentLongitude: float = Field(..., description="여행자의 현재 위치 경도")
    newWeatherCondition: str = Field("RAIN", description="변경된 날씨 상태 (예: RAIN, TYPHOON, SNOW)")
    radiusKm: Optional[float] = Field(5.0, description="대체 장소 탐색 반경 (km)")
    cancelledPlaceId: Optional[Union[str, int, UUID]] = Field(None, description="취소/대체 대상 기존 장소 ID")
    remainingStepsCount: Optional[int] = Field(3, description="남은 일정 슬롯 수")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "regionCode": "6",
                "currentLatitude": 35.1585,
                "currentLongitude": 129.1820,
                "newWeatherCondition": "RAIN",
                "radiusKm": 5.0,
                "remainingStepsCount": 3,
            }
        }
    )


class AIRescheduleResponse(BaseModel):
    """실시간 대체 일정 응답 DTO"""
    message: str = Field(..., description="재추천 안내 메시지")
    originalCondition: Optional[str] = None
    newCondition: str
    recommendedPlaces: List[AISchedulePlace] = Field(..., description="대체 추천된 실내/안전 장소 목록")
    totalDistanceKm: float = Field(..., description="현재 위치로부터 순회 총 이동 거리")
