import sys
import os
import json
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_schedule_service import ai_schedule_service
from app.schemas.ai import AIScheduleResponse, AIDailySchedule, AISchedulePlace, AIRescheduleResponse


def test_api_endpoints():
    client = TestClient(app)

    # 1. Health check
    print("\n--- 1. Health Check Test ---")
    res = client.get("/health")
    print(f"Status Code: {res.status_code}")
    print(res.json())
    assert res.status_code == 200

    # 2. POST /api/v1/ai/schedule
    print("\n--- 2. POST /api/v1/ai/schedule Test ---")
    mock_schedule = AIScheduleResponse(
        tripName="비 오는 가을 부산 감성 힐링 1일 코스",
        weatherSummary="강수확률 80% 우천 예보로 전 일정 실내 문화 및 오션뷰 카페 중심 구성",
        dailySchedules=[
            AIDailySchedule(
                day=1,
                date="2026-10-25",
                weatherCondition="RAIN",
                places=[
                    AISchedulePlace(
                        step=1,
                        placeId="1024",
                        placeName="SEA LIFE 부산아쿠아리움",
                        category="INDOOR_EXHIBITION",
                        startTime="10:30",
                        endTime="12:30",
                        stayTimeMinutes=120,
                        latitude=35.1593,
                        longitude=129.1611,
                        reason="오전 비 예보에 맞춰 비를 맞지 않고 쾌적하게 관람할 수 있는 실내 코스로 선정했습니다.",
                    )
                ]
            )
        ]
    )

    with patch.object(ai_schedule_service, "generate_schedule", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_schedule

        req_payload = {
            "regionCode": "부산",
            "startDate": "2026-10-25",
            "endDate": "2026-10-26",
            "theme": "HEALING",
            "transportation": "PUBLIC",
            "dailyWeathers": [
                {
                    "date": "2026-10-25",
                    "condition": "RAIN",
                    "temp": 16.0,
                    "precipitationProbability": 80
                }
            ]
        }
        res = client.post("/api/v1/ai/schedule", json=req_payload)
        print(f"Status Code: {res.status_code}")
        data = res.json()
        print(f"Trip Name: {data.get('tripName')}")
        print(f"Day 1 Places: {len(data.get('dailySchedules', [{}])[0].get('places', []))}")
        assert res.status_code == 200
        assert data["tripName"] == "비 오는 가을 부산 감성 힐링 1일 코스"

    # 3. POST /api/v1/ai/reschedule
    print("\n--- 3. POST /api/v1/ai/reschedule Test ---")
    mock_reschedule = AIRescheduleResponse(
        message="갑작스러운 RAIN 예보에 따라 현재 위치 반경 5.0km 내 실내 대체 코스로 동선이 재조정되었습니다.",
        newCondition="RAIN",
        recommendedPlaces=[
            AISchedulePlace(
                step=1,
                placeId="2048",
                placeName="해운대 실내 미술관",
                category="INDOOR_EXHIBITION",
                startTime="14:00",
                endTime="15:30",
                stayTimeMinutes=90,
                latitude=35.1612,
                longitude=129.1752,
                reason="우천 시 쾌적한 실내 관람",
            )
        ],
        totalDistanceKm=1.85,
    )

    with patch.object(ai_schedule_service, "reschedule", new_callable=AsyncMock) as mock_resch:
        mock_resch.return_value = mock_reschedule

        resch_payload = {
            "regionCode": "부산",
            "currentLatitude": 35.1585,
            "currentLongitude": 129.1820,
            "newWeatherCondition": "RAIN",
            "radiusKm": 5.0,
            "remainingStepsCount": 2
        }
        res = client.post("/api/v1/ai/reschedule", json=resch_payload)
        print(f"Status Code: {res.status_code}")
        data = res.json()
        print(f"Message: {data.get('message')}")
        print(f"Recommended Count: {len(data.get('recommendedPlaces', []))}")
        assert res.status_code == 200
        assert data["newCondition"] == "RAIN"

    print("\n🎉 모든 API 엔드포인트 연동 테스트 성공!")


if __name__ == "__main__":
    test_api_endpoints()

