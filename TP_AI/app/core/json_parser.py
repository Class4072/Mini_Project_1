import json
import re
from typing import Dict, Any, List, Optional, Set, Union
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
        expected_days: Optional[int] = None,
    ) -> AIScheduleResponse:
        """LLM 원본 응답 텍스트를 AIScheduleResponse로 구조화하고 환각 및 일수를 검증합니다.
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

        # 4. 여행 일수 무결성 검증
        if expected_days and len(schedule_response.dailySchedules) < expected_days:
            app_logger.warning(
                f"[일수 부족 검출] 요청된 여행 일수({expected_days}일)보다 적은 {len(schedule_response.dailySchedules)}일차만 생성됨"
            )
            raise LLMResponseFormatError(
                f"요청된 여행 일수({expected_days}일)보다 적은 {len(schedule_response.dailySchedules)}일차 일정만 생성되었습니다. Day 1부터 Day {expected_days}까지 빠짐없이 모두 생성해야 합니다.",
                raw_text=raw_response,
            )

        # 5. 환각(Hallucination) 검증 및 중복 장소 보정
        if strict_hallucination_check and candidate_places:
            cls.verify_candidates_integrity(schedule_response, candidate_places)

        return schedule_response


    @classmethod
    def verify_candidates_integrity(
        cls,
        schedule: AIScheduleResponse,
        candidate_places: List[Dict[str, Any]],
    ) -> None:
        """반환된 장소들이 실제 후보 목록에 존재하는지 검증하고, ID 오류 및 중복 방문을 안전하게 자동 복구합니다."""
        # 후보 장소들의 ID 및 장소명 맵 생성 (비교 용이하도록 공백/소문자 정규화)
        cand_by_id: Dict[str, Dict[str, Any]] = {}
        cand_by_name: Dict[str, Dict[str, Any]] = {}

        for c in candidate_places:
            c_id = str(c.get("id", "")).strip()
            if c_id:
                cand_by_id[c_id] = c
            c_name = str(c.get("name", "")).strip().replace(" ", "").lower()
            if c_name:
                cand_by_name[c_name] = c

        hallucinated = []
        generic_names = {"카페", "식당", "맛집", "공원", "해변", "바다", "명소", "호텔", "펜션", "숙소"}

        for daily in schedule.dailySchedules:
            for place in daily.places:
                p_id = str(place.placeId).strip()
                p_name = str(place.placeName).strip().replace(" ", "").lower()

                # 1. ID 일치 확인
                matched_cand = cand_by_id.get(p_id)

                # 2. ID 불일치 시 장소명으로 정밀 매칭 및 ID 자동 치유 (Auto-Healing)
                if not matched_cand and p_name and p_name not in generic_names:
                    if p_name in cand_by_name:
                        matched_cand = cand_by_name[p_name]
                    else:
                        for vn, cand in cand_by_name.items():
                            if len(p_name) >= 3 and len(vn) >= 3:
                                if (p_name in vn or vn in p_name):
                                    len_ratio = min(len(p_name), len(vn)) / max(len(p_name), len(vn))
                                    if len_ratio >= 0.5:
                                        matched_cand = cand
                                        break

                if matched_cand:
                    # 후보 장소의 실제 tour_places.id 및 좌표로 보정
                    place.placeId = matched_cand["id"]
                    if matched_cand.get("latitude"):
                        place.latitude = float(matched_cand["latitude"])
                    if matched_cand.get("longitude"):
                        place.longitude = float(matched_cand["longitude"])
                else:
                    hallucinated.append(f"'{place.placeName}' (ID: {place.placeId})")

        if hallucinated:
            app_logger.warning(
                f"[AI 환각 검출] 후보군에 없는 장소 발견: {', '.join(hallucinated)}"
            )
            raise LLMHallucinationError(
                f"후보 장소군에 존재하지 않는 장소가 포함되었습니다: {', '.join(hallucinated)}",
                hallucinated_places=hallucinated,
            )

        # 3. 전체 일정 중복 장소 자동 치유 (각 장소는 전체 일정 중 단 1회만 방문 보장)
        used_place_ids: Set[str] = set()
        for daily in schedule.dailySchedules:
            for place in daily.places:
                p_id_str = str(place.placeId)
                if p_id_str in used_place_ids:
                    alt_cand = next(
                        (c for c in candidate_places if str(c["id"]) not in used_place_ids and c["category"] == place.category),
                        next((c for c in candidate_places if str(c["id"]) not in used_place_ids), None)
                    )
                    if alt_cand:
                        app_logger.info(
                            f"🔄 [중복 장소 치유] Day {daily.day} Step {place.step}: '{place.placeName}'({place.placeId}) -> '{alt_cand['name']}'({alt_cand['id']})"
                        )
                        place.placeId = alt_cand["id"]
                        place.placeName = alt_cand["name"]
                        place.category = alt_cand["category"]
                        place.latitude = float(alt_cand["latitude"])
                        place.longitude = float(alt_cand["longitude"])
                        p_id_str = str(alt_cand["id"])
                used_place_ids.add(p_id_str)


schedule_parser = ScheduleJSONParser()

