import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ai import (
    AIScheduleRequest,
    DailyWeatherInput,
    AIRescheduleRequest,
    AIScheduleResponse,
    AIRescheduleResponse,
)
from app.core.llm_client import llm_client
from app.services.ai_schedule_service import ai_schedule_service


@pytest.mark.asyncio
async def test_llm_retry_and_self_correction():
    """환각 발생 시 피드백 기반 자가보정 재요청 검증"""
    candidate_places = [
        {"id": "p1", "name": "해운대 블루라인파크", "category": "관광", "latitude": 35.16, "longitude": 129.17},
        {"id": "p2", "name": "광안리 카페", "category": "카페", "latitude": 35.15, "longitude": 129.11},
    ]

    req = AIScheduleRequest(
        regionCodes=["6"],
        startDate="2026-11-01",
        endDate="2026-11-01",
        themes=["NATURE"],
    )

    attempt = 0

    async def mock_call(system, user):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            # 1회차: 환각
            return json.dumps({
                "tripName": "환각 일정",
                "weatherSummary": "맑음",
                "dailySchedules": [{
                    "day": 1, "date": "2026-11-01", "weatherCondition": "SUNNY",
                    "places": [{
                        "step": 1, "placeId": "unknown", "placeName": "가짜 장소",
                        "category": "명소", "startTime": "10:00", "endTime": "12:00",
                        "stayTimeMinutes": 120, "latitude": 35.0, "longitude": 129.0, "reason": "환각"
                    }]
                }]
            })
        else:
            # 2회차: 보정된 정상 응답
            assert "긴급 보정 요청" in user
            return json.dumps({
                "tripName": "보정된 부산 일정",
                "weatherSummary": "맑음",
                "dailySchedules": [{
                    "day": 1, "date": "2026-11-01", "weatherCondition": "SUNNY",
                    "places": [{
                        "step": 1, "placeId": "p1", "placeName": "해운대 블루라인파크",
                        "category": "관광", "startTime": "10:00", "endTime": "12:00",
                        "stayTimeMinutes": 120, "latitude": 35.16, "longitude": 129.17, "reason": "정상 추천"
                    }]
                }]
            })

    with patch.object(llm_client, "_call_provider_raw", side_effect=mock_call):
        schedule = await llm_client.generate_schedule_with_retry(req, candidate_places)

    assert attempt == 2
    assert schedule.dailySchedules[0].places[0].placeName == "해운대 블루라인파크"


def test_api_schedule_endpoint_draft_spec():
    """02_요청 데이터 명세 초안 페이로드로 POST /api/v1/ai/schedule 호출 검증"""
    client = TestClient(app)

    payload = {
        "regionCodes": ["6"],
        "startDate": "2026-11-01",
        "endDate": "2026-11-03",
        "companionType": "FRIENDS",
        "travelerCount": 3,
        "transport": "PUBLIC_TRANSIT",
        "themes": ["FOOD", "NATURE"],
        "placesPerDay": "NORMAL",
        "startTime": "NORMAL"
    }

    mock_resp = AIScheduleResponse(
        tripName="부산 미식·자연 친구와 함께하는 3일 코스",
        weatherSummary="11월 초 상쾌한 가을 날씨 대중교통 최적화 코스",
        dailySchedules=[]
    )

    with patch.object(ai_schedule_service, "generate_schedule", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_resp
        res = client.post("/api/v1/ai/schedule", json=payload)
        assert res.status_code == 200
        assert res.json()["tripName"] == "부산 미식·자연 친구와 함께하는 3일 코스"


@pytest.mark.asyncio
async def test_multi_region_branching():
    """복수 지역코드 (예: 부산 6, 울산 7) 요청 시 전용 메서드로 분기 처리 검증"""
    multi_req = AIScheduleRequest(
        regionCodes=["6", "7"],
        startDate="2026-11-01",
        endDate="2026-11-03",
        companionType="FRIENDS",
        themes=["FOOD", "NATURE"],
    )

    mock_db = AsyncMock()

    # 복수 지역 전용 메서드가 분기 호출되는지 mock 검증
    mock_multi_resp = AIScheduleResponse(
        tripName="부산·울산 연계 3일 힐링 코스",
        weatherSummary="부산과 울산을 아우르는 연계 일정",
        dailySchedules=[]
    )

    with patch.object(ai_schedule_service, "_generate_multi_region_schedule", new_callable=AsyncMock) as mock_multi:
        mock_multi.return_value = mock_multi_resp
        result = await ai_schedule_service.generate_schedule(mock_db, multi_req)
        
        # 복수 지역 전용 메서드가 호출되었는지 확인
        assert mock_multi.called
        assert result.tripName == "부산·울산 연계 3일 힐링 코스"
        # 호출 인자에 '부산', '울산'이 정상 전달되었는지 확인
        args, kwargs = mock_multi.call_args
        assert "부산" in args[2]
        assert "울산" in args[2]


def test_invalid_date_range_validation():
    """종료일이 시작일보다 앞서는 잘못된 날짜 요청 시 422/ValueError 검증 차단 확인"""
    with pytest.raises(ValueError) as exc_info:
        AIScheduleRequest(
            regionCodes=["6"],
            startDate="2026-11-05",
            endDate="2026-11-01",  # 종료일이 시작일보다 이전
            companionType="FRIENDS",
        )
    assert "여행 종료일" in str(exc_info.value)
    assert "이후여야 합니다" in str(exc_info.value)


@pytest.mark.asyncio
async def test_reschedule_sequential_distance_and_clamping():
    """실시간 재추천 시 실제 순차 주행 거리 누적 및 21:00 클램핑 검증"""
    req = AIRescheduleRequest(
        regionCode="6",
        currentLatitude=35.1585,
        currentLongitude=129.1820,
        newWeatherCondition="RAIN",
        remainingStepsCount=3,
    )

    # 3개 가상 장소 DB Mock 설정
    class MockSpot:
        def __init__(self, id, name, cat, lat, lon):
            self.id = id
            self.name = name
            self.category = cat
            self.latitude = lat
            self.longitude = lon
            self.address = f"부산 {name}"
            self.description = f"{name} 설명"
            self.spot_metadata = {"is_indoor": True}

    spots = [
        MockSpot("s1", "해운대 아쿠아리움", "실내/아쿠아리움", 35.1590, 129.1830),
        MockSpot("s2", "센텀 신세계 스파랜드", "실내/스파", 35.1689, 129.1296),
        MockSpot("s3", "부산 시립미술관", "실내/미술관", 35.1663, 129.1368),
    ]

    mock_db = AsyncMock()
    from unittest.mock import MagicMock
    mock_res = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = spots
    mock_res.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_res

    with patch("app.core.embedding.embedding_service.embed_text", return_value=[0.1] * 768):
        res = await ai_schedule_service.reschedule(mock_db, req)

    # 검증 1: 장소 개수
    assert len(res.recommendedPlaces) == 3
    # 검증 2: 각 장소의 구간 거리(distanceFromPrevKm) 및 이동 시간(estimatedTravelMinutes) 존재
    for p in res.recommendedPlaces:
        assert p.distanceFromPrevKm is not None
        assert p.estimatedTravelMinutes is not None
        # 검증 3: 시각 21:00 클램핑 및 두 자릿수 포맷
        hour = int(p.endTime.split(":")[0])
        assert hour <= 21

    # 검증 4: totalDistanceKm이 각 구간(현재위치->1, 1->2, 2->3)의 실제 합산과 일치
    expected_sum = sum(p.distanceFromPrevKm for p in res.recommendedPlaces)
    assert round(res.totalDistanceKm, 1) == round(expected_sum, 1)


def test_fallback_schedule_time_clamping():
    """Fallback 일정 생성 시 6개 이상 장소여도 24시 오버플로우 없이 21:00 내로 종료되는지 검증"""
    req = AIScheduleRequest(
        regionCodes=["6"],
        startDate="2026-11-01",
        endDate="2026-11-01",
        placesPerDay="PACKED",
        startTime="LATE",  # 11:00 시작
    )
    candidate_places = [
        {"id": f"p{i}", "name": f"장소 {i}", "category": "관광", "latitude": 35.1 + i*0.01, "longitude": 129.1}
        for i in range(8)
    ]

    fallback = llm_client.build_fallback_schedule(req, candidate_places)
    day1 = fallback.dailySchedules[0]
    last_place = day1.places[-1]
    
    # 마지막 장소의 종료 시각 확인
    last_end_hour = int(last_place.endTime.split(":")[0])
    assert last_end_hour <= 21
    # 24:00, 25:00 등의 유효하지 않은 시각이 없음을 확인
    for p in day1.places:
        h = int(p.endTime.split(":")[0])
        assert 0 <= h <= 21





