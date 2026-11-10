import sys
import os
import json
import asyncio
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.ai import AIScheduleRequest, DailyWeatherInput, AIScheduleResponse
from app.core.json_parser import (
    schedule_parser,
    LLMResponseFormatError,
    LLMHallucinationError,
)
from app.core.llm_client import llm_client
from app.core.prompt_builder import prompt_builder


def print_title(title: str):
    print(f"\n{'='*25} {title} {'='*25}")


def test_1_normal_json_parsing():
    print_title("1. 마크다운 포함 정상 JSON 파싱 테스트")
    candidate_places = [
        {"id": "spot_101", "name": "해운대 해수욕장", "category": "자연", "latitude": 35.1587, "longitude": 129.1603},
        {"id": "spot_102", "name": "부산 시립미술관", "category": "문화/실내", "latitude": 35.1664, "longitude": 129.1365},
    ]

    raw_llm_output = """
    안녕하세요! 요청하신 부산 힐링 여행 일정입니다:
    ```json
    {
      "tripName": "비 오는 가을 부산 감성 힐링 1일 코스",
      "weatherSummary": "강수확률 80% 우천 예보로 전 일정 실내 문화 및 오션뷰 카페 중심 구성",
      "dailySchedules": [
        {
          "day": 1,
          "date": "2026-10-25",
          "weatherCondition": "RAIN",
          "places": [
            {
              "step": 1,
              "placeId": "spot_102",
              "placeName": "부산 시립미술관",
              "category": "문화/실내",
              "startTime": "10:30",
              "endTime": "12:30",
              "stayTimeMinutes": 120,
              "latitude": 35.1664,
              "longitude": 129.1365,
              "reason": "비 오는 날 실내에서 쾌적하게 예술을 감상할 수 있습니다."
            }
          ]
        }
      ]
    }
    ```
    즐거운 여행 되시길 바랍니다!
    """

    schedule = schedule_parser.parse_and_validate(
        raw_response=raw_llm_output,
        candidate_places=candidate_places,
    )
    print(f"✅ 파싱 성공!")
    print(f"여행명: {schedule.tripName}")
    print(f"날씨 요약: {schedule.weatherSummary}")
    print(f"일정 장소: {schedule.dailySchedules[0].places[0].placeName} (ID: {schedule.dailySchedules[0].places[0].placeId})")
    assert schedule.tripName == "비 오는 가을 부산 감성 힐링 1일 코스"
    assert len(schedule.dailySchedules[0].places) == 1


def test_2_broken_json_format_error():
    print_title("2. 깨진 JSON / 포맷 오류 감지 테스트")
    candidate_places = [{"id": "1", "name": "광안리"}]
    broken_llm_output = """
    ```json
    {
      "tripName": "부산 여행",
      "weatherSummary": "맑음",
      "dailySchedules": [
        { "day": 1, "date": "2026-10-25" ... [JSON 문법 깨짐]
    ```
    """

    try:
        schedule_parser.parse_and_validate(broken_llm_output, candidate_places)
        print("❌ 테스트 실패: 예외가 발생해야 합니다.")
    except LLMResponseFormatError as e:
        print(f"✅ 의도된 포맷 오류 예외 포착 성공: {e.message}")


def test_3_hallucination_detection():
    print_title("3. AI 환각(Candidate 외 장소 날조) 검출 테스트")
    candidate_places = [
        {"id": "spot_101", "name": "해운대 해수욕장"},
        {"id": "spot_102", "name": "부산 시립미술관"},
    ]

    # LLM이 후보군에 없는 가짜 장소 "달나라 스카이워크"를 날조한 경우
    hallucinated_llm_output = json.dumps({
        "tripName": "환각 여행 코스",
        "weatherSummary": "비 옴",
        "dailySchedules": [
            {
                "day": 1,
                "date": "2026-10-25",
                "weatherCondition": "RAIN",
                "places": [
                    {
                        "step": 1,
                        "placeId": "fake_spot_999",
                        "placeName": "달나라 스카이워크 (가짜 장소)",
                        "category": "액티비티",
                        "startTime": "10:00",
                        "endTime": "12:00",
                        "stayTimeMinutes": 120,
                        "latitude": 35.0,
                        "longitude": 129.0,
                        "reason": "환각으로 지어낸 가상 스팟"
                    }
                ]
            }
        ]
    })

    try:
        schedule_parser.parse_and_validate(hallucinated_llm_output, candidate_places)
        print("❌ 테스트 실패: 환각 예외가 발생해야 합니다.")
    except LLMHallucinationError as e:
        print(f"✅ 의도된 환각 검출 예외 포착 성공!")
        print(f"에러 메시지: {e.message}")
        print(f"날조된 장소 목록: {e.hallucinated_places}")
        assert "달나라 스카이워크 (가짜 장소)" in str(e.hallucinated_places[0])


async def test_4_retry_and_self_correction():
    print_title("4. 오류 피드백 기반 자동 재요청(Self-Correction) 시뮬레이션")
    
    candidate_places = [
        {"id": "p1", "name": "해운대 블루라인파크", "category": "관광", "latitude": 35.16, "longitude": 129.17, "description": "해변열차"},
        {"id": "p2", "name": "광안리 오션뷰 카페", "category": "카페", "latitude": 35.15, "longitude": 129.11, "description": "광안대교 뷰"},
    ]

    req = AIScheduleRequest(
        regionCode="부산",
        startDate="2026-10-25",
        endDate="2026-10-25",
        theme="HEALING",
        dailyWeathers=[DailyWeatherInput(date="2026-10-25", condition="RAIN", temp=18.0)]
    )

    # 1회차: 환각 발생 ("환각랜드")
    # 2회차: 피드백 반영 후 정상 응답 ("해운대 블루라인파크")
    attempt_count = 0

    async def mock_call_provider(system_prompt: str, user_prompt: str) -> str:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            print("  [Mock LLM 1회차] 환각 장소가 포함된 응답 반환")
            return json.dumps({
                "tripName": "1회차 일정",
                "weatherSummary": "비",
                "dailySchedules": [{
                    "day": 1, "date": "2026-10-25", "weatherCondition": "RAIN",
                    "places": [{
                        "step": 1, "placeId": "unknown_999", "placeName": "환각랜드",
                        "category": "테마파크", "startTime": "10:00", "endTime": "12:00",
                        "stayTimeMinutes": 120, "latitude": 35.0, "longitude": 129.0, "reason": "날조됨"
                    }]
                }]
            })
        else:
            print(f"  [Mock LLM 2회차] 피드백을 수신하여 정상 장소로 보정된 응답 반환")
            assert "긴급 보정 요청" in user_prompt, "User Prompt에 피드백이 누락되었습니다!"
            return json.dumps({
                "tripName": "보정된 비 오는 부산 힐링 코스",
                "weatherSummary": "실내 및 해변열차 코스",
                "dailySchedules": [{
                    "day": 1, "date": "2026-10-25", "weatherCondition": "RAIN",
                    "places": [{
                        "step": 1, "placeId": "p1", "placeName": "해운대 블루라인파크",
                        "category": "관광", "startTime": "10:00", "endTime": "12:00",
                        "stayTimeMinutes": 120, "latitude": 35.16, "longitude": 129.17, "reason": "비 오는 바다 풍경 관람"
                    }]
                }]
            })

    with patch.object(llm_client, "_call_provider_raw", side_effect=mock_call_provider):
        result = await llm_client.generate_schedule_with_retry(req, candidate_places)

    print(f"✅ 재시도 및 자가보정 성공!")
    print(f"총 호출 횟수: {attempt_count}회")
    print(f"최종 일정명: {result.tripName}")
    print(f"장소명: {result.dailySchedules[0].places[0].placeName}")
    assert attempt_count == 2
    assert result.dailySchedules[0].places[0].placeName == "해운대 블루라인파크"


async def test_5_fallback_when_retries_exhausted():
    print_title("5. 재시도 초과 시 Fallback Generator 가동 테스트")
    candidate_places = [
        {"id": "p1", "name": "자갈치 시장", "category": "맛집", "latitude": 35.09, "longitude": 129.03, "description": "수산시장"},
    ]
    req = AIScheduleRequest(
        regionCode="부산",
        startDate="2026-10-25",
        endDate="2026-10-25",
        theme="FOOD",
    )

    # 항상 에러를 반환하는 LLM 시뮬레이션
    async def always_broken_llm(s, u):
        return "이것은 유효하지 않은 텍스트입니다."

    with patch.object(llm_client, "_call_provider_raw", side_effect=always_broken_llm):
        fallback_res = await llm_client.generate_schedule_with_retry(req, candidate_places)

    print(f"✅ Fallback 가동 성공!")
    print(f"일정명: {fallback_res.tripName}")
    print(f"총 장소 수: {len(fallback_res.dailySchedules[0].places)}")
    print(f"선정된 장소: {fallback_res.dailySchedules[0].places[0].placeName}")
    assert fallback_res.dailySchedules[0].places[0].placeName == "자갈치 시장"


async def main():
    test_1_normal_json_parsing()
    test_2_broken_json_format_error()
    test_3_hallucination_detection()
    await test_4_retry_and_self_correction()
    await test_5_fallback_when_retries_exhausted()
    print("\n🎉 모든 파싱 및 환각/재시도 단위 테스트 통과 완료!")


if __name__ == "__main__":
    asyncio.run(main())

