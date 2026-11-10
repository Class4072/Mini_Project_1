import pytest
from app.core.json_parser import (
    schedule_parser,
    LLMResponseFormatError,
    LLMHallucinationError,
)
from app.core.prompt_builder import prompt_builder
from app.core.code_mapper import code_mapper
from app.schemas.ai import AIScheduleRequest, DailyWeatherInput


class TestJSONParserAndHallucination:
    """응답 파싱 및 AI 환각 검증 테스트"""

    def setup_method(self):
        self.candidate_places = [
            {"id": "spot_1", "name": "해운대 해수욕장", "category": "자연", "latitude": 35.1587, "longitude": 129.1603},
            {"id": "spot_2", "name": "부산 시립미술관", "category": "문화/실내", "latitude": 35.1664, "longitude": 129.1365},
            {"id": "spot_3", "name": "광안리 오션뷰 카페", "category": "카페", "latitude": 35.1530, "longitude": 129.1180},
        ]

    def test_markdown_json_parsing_success(self):
        """마크다운 코드블록과 부가 텍스트가 포함된 정상 응답 파싱"""
        raw_text = """
        네! 추천 코스입니다:
        ```json
        {
          "tripName": "부산 감성 힐링 1일 코스",
          "weatherSummary": "맑은 날씨에 어울리는 바다와 미술관 코스",
          "dailySchedules": [
            {
              "day": 1,
              "date": "2026-11-01",
              "weatherCondition": "SUNNY",
              "places": [
                {
                  "step": 1,
                  "placeId": "spot_1",
                  "placeName": "해운대 해수욕장",
                  "category": "자연",
                  "startTime": "10:00",
                  "endTime": "12:00",
                  "stayTimeMinutes": 120,
                  "latitude": 35.1587,
                  "longitude": 129.1603,
                  "reason": "화창한 날씨에 바다 산책하기 좋습니다."
                }
              ]
            }
          ]
        }
        ```
        즐거운 여행 되세요!
        """
        schedule = schedule_parser.parse_and_validate(raw_text, self.candidate_places)
        assert schedule.tripName == "부산 감성 힐링 1일 코스"
        assert len(schedule.dailySchedules) == 1
        assert schedule.dailySchedules[0].places[0].placeName == "해운대 해수욕장"

    def test_broken_json_syntax_error(self):
        """문법이 깨진 JSON 응답 시 LLMResponseFormatError 발생 확인"""
        broken_json = '{"tripName": "부산 코스", "dailySchedules": [ { "day": 1 ... [문법오류]}'
        with pytest.raises(LLMResponseFormatError):
            schedule_parser.parse_and_validate(broken_json, self.candidate_places)

    def test_schema_missing_fields_error(self):
        """필수 키가 누락된 경우 Pydantic 검증 오류 확인"""
        incomplete_json = '{"tripName": "부산 코스"}'  # dailySchedules 누락
        with pytest.raises(LLMResponseFormatError):
            schedule_parser.parse_and_validate(incomplete_json, self.candidate_places)

    def test_auto_repair_trailing_comma(self):
        """Trailing Comma(끝 쉼표) 등 경미한 JSON 문법 오류를 재시도 없이 자체 Auto-Repair 성공 검증"""
        trailing_comma_json = """
        {
          "tripName": "부산 힐링 코스",
          "weatherSummary": "쾌적한 날씨,",
          "dailySchedules": [
            {
              "day": 1,
              "date": "2026-11-01",
              "weatherCondition": "SUNNY",
              "places": [
                {
                  "step": 1,
                  "placeId": "spot_1",
                  "placeName": "해운대 해수욕장",
                  "category": "자연",
                  "startTime": "10:00",
                  "endTime": "12:00",
                  "stayTimeMinutes": 120,
                  "latitude": 35.1587,
                  "longitude": 129.1603,
                  "reason": "해변 산책",
                },
              ],
            },
          ],
        }
        """
        # 끝 쉼표가 여러 개 있어도 json_parser가 Auto-Repair하여 에러 없이 통과해야 함!
        schedule = schedule_parser.parse_and_validate(trailing_comma_json, self.candidate_places)
        assert schedule.tripName == "부산 힐링 코스"
        assert schedule.dailySchedules[0].places[0].placeName == "해운대 해수욕장"

    def test_hallucination_place_detection(self):
        """후보군 외 가짜 장소 날조 시 LLMHallucinationError 발생 확인"""
        hallucinated_json = """
        {
          "tripName": "부산 코스",
          "weatherSummary": "맑음",
          "dailySchedules": [
            {
              "day": 1,
              "date": "2026-11-01",
              "weatherCondition": "SUNNY",
              "places": [
                {
                  "step": 1,
                  "placeId": "fake_999",
                  "placeName": "화성 탐사 기지 (가짜 장소)",
                  "category": "체험",
                  "startTime": "10:00",
                  "endTime": "12:00",
                  "stayTimeMinutes": 120,
                  "latitude": 35.0,
                  "longitude": 129.0,
                  "reason": "환각 장소"
                }
              ]
            }
          ]
        }
        """
        with pytest.raises(LLMHallucinationError) as exc_info:
            schedule_parser.parse_and_validate(hallucinated_json, self.candidate_places)
        assert "화성 탐사 기지" in str(exc_info.value)

