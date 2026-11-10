import sys
import os
import json
import datetime
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.ai import AIScheduleRequest, AIScheduleResponse
from app.core.prompt_builder import prompt_builder
from app.core.code_mapper import code_mapper
from app.services.ai_schedule_service import ai_schedule_service


def test_draft_spec_request():
    print("=" * 60)
    print("🧪 [02_요청 데이터 명세 초안.md] JSON 페이로드 파싱 & 처리 검증")
    print("=" * 60)

    # 1. 02_명세서에 정의된 정확한 JSON 페이로드
    draft_payload = {
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

    print("\n[Step 1] Pydantic DTO (AIScheduleRequest) 파싱 검증")
    req = AIScheduleRequest.model_validate(draft_payload)
    print(f"✅ 파싱 성공:")
    print(f"  - regionCodes: {req.regionCodes}")
    print(f"  - 기간: {req.startDate} ~ {req.endDate}")
    print(f"  - 동행: {req.companionType} ({req.travelerCount}인)")
    print(f"  - 이동수단: {req.transport}")
    print(f"  - 테마: {req.themes}")
    print(f"  - 장소밀도: {req.placesPerDay}, 시작시간: {req.startTime}")

    assert req.regionCodes == ["6"]
    assert req.companionType == "FRIENDS"
    assert req.travelerCount == 3
    assert req.themes == ["FOOD", "NATURE"]

    print("\n[Step 2] CodeMapper를 통한 메타데이터 변환 검증")
    region_name = code_mapper.resolve_region_name(req.regionCodes[0])
    companion_name, companion_tags = code_mapper.get_companion_info(req.companionType, req.travelerCount)
    themes_desc = code_mapper.get_theme_descriptions(req.themes)
    spots_per_day = code_mapper.get_spots_per_day(req.placesPerDay)
    start_hour = code_mapper.get_start_time_hour(req.startTime)

    print(f"  - 지역 코드 '6' -> '{region_name}'")
    print(f"  - 동행 코드 'FRIENDS' -> '{companion_name}' (태그: {companion_tags})")
    print(f"  - 테마 코드 ['FOOD', 'NATURE'] -> '{themes_desc}'")
    print(f"  - placesPerDay 'NORMAL' -> 하루 {spots_per_day}곳")
    print(f"  - startTime 'NORMAL' -> {start_hour}:00 시작")

    assert region_name == "부산"
    assert companion_name == "친구"
    assert spots_per_day == 4
    assert start_hour == 10

    print("\n[Step 3] PromptBuilder 프롬프트 생성 검증")
    candidate_places = [
        {"id": "b1", "name": "광안리 해수욕장", "category": "자연", "latitude": 35.15, "longitude": 129.11},
        {"id": "b2", "name": "해운대 기와집 대구탕", "category": "맛집", "latitude": 35.16, "longitude": 129.17},
        {"id": "b3", "name": "달맞이길 카페", "category": "카페", "latitude": 35.15, "longitude": 129.18},
    ]
    user_prompt = prompt_builder.build_user_prompt(req, candidate_places)
    print("생성된 User Prompt 요약:")
    for line in user_prompt.split("\n")[:12]:
        print(f"  | {line}")

    assert "부산" in user_prompt
    assert "친구" in user_prompt
    assert "미식·맛집" in user_prompt

    print("\n[Step 4] FastAPI POST /api/v1/ai/schedule 실제 API 엔드포인트 호출 검증")
    client = TestClient(app)

    # Mocking generate_schedule
    mock_resp = AIScheduleResponse(
        tripName="부산 미식·자연 친구와 함께하는 3일 코스",
        weatherSummary="11월 초 상쾌한 가을 날씨에 맞춘 대중교통 최적화 코스",
        dailySchedules=[]
    )
    with patch.object(ai_schedule_service, "generate_schedule", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_resp
        res = client.post("/api/v1/ai/schedule", json=draft_payload)
        print(f"  Response Status: {res.status_code}")
        print(f"  Response Body: {res.json()}")
        assert res.status_code == 200
        assert res.json()["tripName"] == "부산 미식·자연 친구와 함께하는 3일 코스"

    print("\n" + "=" * 60)
    print("🎉 [02_요청 데이터 명세 초안.md] 연동 검증 100% 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_draft_spec_request()

