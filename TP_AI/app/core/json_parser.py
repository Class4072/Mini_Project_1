import json
import re
from typing import Dict, Any, List, Set, Union
from uuid import UUID
from pydantic import ValidationError

from app.schemas.ai import AIScheduleResponse, AIDailySchedule, AISchedulePlace
from app.core.logger import app_logger


class LLMResponseFormatError(Exception):
    """LLM 응답이 올바른 JSON 형식이 아니거나 스키마와 불일치할 때 발생"""
    def __init__(self, message: str, raw_text: str):
        super().__init__(message)
        self.message = message
        self.raw_text = raw_text


class LLMHallucinationError(Exception):
    """LLM이 후보 장소군에 없는 장소를 임의로 날조(환각)했을 때 발생"""
    def __init__(self, message: str, hallucinated_places: List[str]):
        super().__init__(message)
        self.message = message
        self.hallucinated_places = hallucinated_places


class ScheduleJSONParser:
    """LLM 여행 일정 응답 파싱 및 AI 환각(Hallucination) 검증기"""

    @classmethod
    def clean_json_string(cls, raw_text: str) -> str:
        """마크다운 코드블록 및 앞뒤 부가 텍스트 제거 후 순수 JSON 블록만 추출"""
        text = raw_text.strip()

        # 1. ```json ... ``` 또는 ``` ... ``` 마크다운 코드블록 제거
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()

        # 2. 첫 번째 '{' 부터 마지막 '}' 까지 추출 (앞뒤 불필요한 인사말 제거)
        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace : last_brace + 1].strip()

        return text

    @classmethod
    def repair_json_syntax(cls, json_str: str) -> str:
        """LLM이 자주 범하는 JSON 문법 오류(Trailing comma 등)를 자동으로 복구"""
        text = json_str

        # 1. 객체/배열 끝 쉼표(Trailing Comma: ,} 또는 ,] ) 제거
        text = re.sub(r",\s*([}\]])", r"\1", text)

        # 2. 주석(// ...) 제거
        text = re.sub(r"//.*?\n", "\n", text)

        return text

    @classmethod
    def parse_and_validate(
        cls,
        raw_response: str,
        candidate_places: List[Dict[str, Any]],
        strict_hallucination_check: bool = True,
    ) -> AIScheduleResponse:
        """LLM 원본 응답 텍스트를 AIScheduleResponse로 구조화하고 환각 여부를 검증합니다.
        문법 오류 발생 시 1차 자동 복구(Auto-Repair)를 시도합니다.
        """
        # 1. 텍스트 정제
        cleaned = cls.clean_json_string(raw_response)

        # 2. JSON 로드 (1차 일반 로드 -> 실패 시 Auto-Repair 후 재시도)
        data = None
        decode_err = None
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            decode_err = e
            # 자동 문법 복구 시도
            try:
                repaired = cls.repair_json_syntax(cleaned)
                data = json.loads(repaired)
                app_logger.info("🔧 [JSON Auto-Repair 성공] 끝 쉼표/문법 오류를 자체 복구하여 파싱에 성공했습니다.")
                decode_err = None
            except Exception:
                pass

        if decode_err is not None or data is None:
            app_logger.warning(
                f"[JSON 파싱 실패] 위치: 라인 {decode_err.lineno}, 컬럼 {decode_err.colno} ({decode_err.msg}) | 원본 미리보기: {cleaned[:150]}"
            )
            raise LLMResponseFormatError(
                f"JSON 디코딩 실패 (line {decode_err.lineno}, col {decode_err.colno}): {decode_err.msg}",
                raw_text=raw_response,
            )

        # 3. Pydantic 스키마 검증
        try:
            schedule_response = AIScheduleResponse.model_validate(data)
        except ValidationError as e:
            app_logger.warning(f"[Pydantic 스키마 검증 실패] {e.error_count()}개의 필드 오류 발생: {e}")
            raise LLMResponseFormatError(
                f"Pydantic 스키마 검증 실패: {e.errors()}",
                raw_text=raw_response,
            )

        # 4. 환각(Hallucination) 검증
        if strict_hallucination_check and candidate_places:
            cls.verify_candidates_integrity(schedule_response, candidate_places)

        return schedule_response


    @classmethod
    def verify_candidates_integrity(
        cls,
        schedule: AIScheduleResponse,
        candidate_places: List[Dict[str, Any]],
    ) -> None:
        """반환된 장소들이 실제 후보 목록에 존재하는지 검증 (AI 환각 방지)"""
        # 후보 장소들의 ID 및 장소명 집합 생성 (비교 용이하도록 공백/소문자 정규화)
        valid_ids: Set[str] = set()
        valid_names: Set[str] = set()

        for c in candidate_places:
            c_id = str(c.get("id", "")).strip()
            if c_id:
                valid_ids.add(c_id)
            c_name = str(c.get("name", "")).strip().replace(" ", "").lower()
            if c_name:
                valid_names.add(c_name)

        hallucinated = []
        generic_names = {"카페", "식당", "맛집", "공원", "해변", "바다", "명소", "호텔", "펜션", "숙소"}

        for daily in schedule.dailySchedules:
            for place in daily.places:
                p_id = str(place.placeId).strip()
                p_name = str(place.placeName).strip().replace(" ", "").lower()

                # 1. ID 일치 확인
                id_matched = p_id in valid_ids

                # 2. 이름 일치 정밀 확인 (일반 명사 악용 및 1~2글자 느슨한 부분 일치 방어)
                name_matched = False
                if p_name and p_name not in generic_names:
                    for vn in valid_names:
                        if p_name == vn:
                            name_matched = True
                            break
                        # 3글자 이상이며, 상호 부분 포함 관계이고 길이 비율이 0.5 이상일 때만 유사 인정
                        if len(p_name) >= 3 and len(vn) >= 3:
                            if (p_name in vn or vn in p_name):
                                len_ratio = min(len(p_name), len(vn)) / max(len(p_name), len(vn))
                                if len_ratio >= 0.5:
                                    name_matched = True
                                    break

                if not (id_matched or name_matched):
                    hallucinated.append(f"'{place.placeName}' (ID: {place.placeId})")

        if hallucinated:
            app_logger.warning(
                f"[AI 환각 검출] 후보군에 없는 장소 발견: {', '.join(hallucinated)}"
            )
            raise LLMHallucinationError(
                f"후보 장소군에 존재하지 않는 장소가 포함되었습니다: {', '.join(hallucinated)}",
                hallucinated_places=hallucinated,
            )


schedule_parser = ScheduleJSONParser()

