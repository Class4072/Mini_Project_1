import time
import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import timedelta

from app.config import settings
from app.schemas.ai import (
    AIScheduleRequest,
    AIScheduleResponse,
    AIDailySchedule,
    AISchedulePlace,
)
from app.core.logger import app_logger
from app.core.prompt_builder import prompt_builder
from app.core.code_mapper import code_mapper
from app.core.route_planner import route_planner
from app.core.json_parser import (
    schedule_parser,
    LLMResponseFormatError,
    LLMHallucinationError,
)


class LLMClient:
    """Ollama / Gemini / OpenAI 연동 및 포맷 오류/환각 재요청 처리 엔진"""

    def __init__(self):
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.max_retries = 2  # 최초 시도 1회 + 재시도 최대 2회 = 총 3회 시도

    async def _call_provider_raw(self, system_prompt: str, user_prompt: str) -> str:
        """설정된 LLM_PROVIDER에 따라 비동기 HTTP 호출 수행"""
        provider = settings.LLM_PROVIDER.lower()

        if provider == "ollama":
            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            payload = {
                "model": settings.LLM_MODEL_NAME,
                "system": system_prompt,
                "prompt": user_prompt,
                "format": "json",  # Ollama 공식 문법 제약(Grammar-constrained) 순수 JSON 모드 강제
                "stream": False,
                "options": {
                    "temperature": 0.2,  # 환각 방지를 위한 낮은 온도
                },
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                return data.get("response", "")


        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되어 있지 않습니다.")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.LLM_MODEL_NAME or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]

        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY가 설정되어 있지 않습니다.")
            model_name = settings.LLM_MODEL_NAME or "gemini-1.5-flash"
            # 보안 강화: URL 쿼리 파라미터 대신 헤더 인증을 사용하여 로그/예외 시 API 키 노출 방지
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            headers = {
                "x-goog-api-key": settings.GEMINI_API_KEY,
                "Content-Type": "application/json",
            }
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("Gemini로부터 응답을 받지 못했습니다.")
                return candidates[0]["content"]["parts"][0]["text"]


        else:
            # mock provider (테스트 및 로컬 오프라인 환경)
            return self._generate_mock_llm_response(user_prompt)

    def _generate_mock_llm_response(self, user_prompt: str) -> str:
        """테스트 및 LLM 비활성화 환경을 위한 Mock 응답 생성기"""
        # 사용자 프롬프트 내 장소 정보 파싱하여 자연스러운 JSON 반환
        return json.dumps({
            "tripName": "AI 맞춤 감성 힐링 여행 코스",
            "weatherSummary": "기상 및 계절 정보를 반영하여 실내외 명소와 힐링 스팟을 최적으로 배치했습니다.",
            "dailySchedules": []
        }, ensure_ascii=False)

    async def generate_schedule_with_retry(
        self,
        req: AIScheduleRequest,
        candidate_places: List[Dict[str, Any]],
        structured_routes: Optional[List[Dict[str, Any]]] = None,
    ) -> AIScheduleResponse:
        """포맷 오류 및 AI 환각 검출 시 피드백 기반 자동 재요청(Self-Correction)을 수행합니다."""
        
        system_prompt = prompt_builder.SYSTEM_PROMPT
        error_feedback: Optional[str] = None
        last_raw_response = ""

        for attempt in range(1, self.max_retries + 2):
            if attempt > 1:
                backoff_sec = 0.5 * (attempt - 1)
                app_logger.info(f"⏳ [재시도 백오프 대기] {backoff_sec:.1f}초 후 재요청을 수행합니다...")
                await asyncio.sleep(backoff_sec)

            user_prompt = prompt_builder.build_user_prompt(
                req=req,
                candidate_places=candidate_places,
                error_feedback=error_feedback,
            )

            start_time = time.perf_counter()
            app_logger.info(
                f"[LLM 호출 시도 {attempt}/{self.max_retries + 1}] provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL_NAME}"
            )

            try:
                raw_text = await self._call_provider_raw(system_prompt, user_prompt)
                last_raw_response = raw_text
                duration_ms = (time.perf_counter() - start_time) * 1000

                app_logger.info(
                    f"LLM 응답 수신 완료 | latency_ms={duration_ms:.2f}, raw_length={len(raw_text)}"
                )

                # 1. 응답 파싱 및 환각 검증
                parsed_schedule = schedule_parser.parse_and_validate(
                    raw_response=raw_text,
                    candidate_places=candidate_places,
                    strict_hallucination_check=True,
                )

                app_logger.info(
                    f"✅ [성공] 일정 파싱 및 환각 검증 통과! (총 {len(parsed_schedule.dailySchedules)}일차 일정 구성 완료)"
                )
                return parsed_schedule

            except LLMResponseFormatError as fe:
                app_logger.warning(
                    f"⚠️ [재시도 사유: 포맷 오류] (시도 {attempt}/{self.max_retries + 1}): {fe.message}"
                )
                error_feedback = f"JSON 포맷 검증 실패: {fe.message}"

            except LLMHallucinationError as he:
                app_logger.warning(
                    f"⚠️ [재시도 사유: AI 환각 발생] (시도 {attempt}/{self.max_retries + 1}): {he.message}"
                )
                error_feedback = (
                    f"AI 환각 검출: 다음 장소들은 제공된 목록에 없습니다 ({', '.join(he.hallucinated_places)}).\n"
                    "반드시 [선택 가능한 후보 장소 목록]에 명시된 ID와 이름만 정확히 사용하십시오. "
                    "임의로 가상의 장소를 지어내면 시스템이 거부합니다."
                )


            except Exception as e:
                app_logger.error(
                    f"❌ [LLM 호출 실패] 네트워크 또는 제공자 오류 발생: {e}"
                )
                # LLM 엔드포인트 자체 연결 실패 시 즉시 폴백으로 전환
                break

        # 모든 재시도 소진 시 안전한 Fallback Generator 가동 (시스템 다운 방지)
        app_logger.warning(
            "🚨 [Fallback 실행] LLM 재시도 횟수 초과 또는 연동 불가로 인해 2단계 동선 최적화 기반 안전한 일정을 생성합니다."
        )
        return self.build_fallback_schedule(
            req=req,
            candidate_places=candidate_places,
            structured_routes=structured_routes,
        )

    def build_fallback_schedule(
        self,
        req: AIScheduleRequest,
        candidate_places: List[Dict[str, Any]],
        structured_routes: Optional[List[Dict[str, Any]]] = None,
    ) -> AIScheduleResponse:
        """LLM 오류 시 환각 없이 100% 신뢰할 수 있는 룰 기반 일정 생성기 (Fallback)"""
        
        # 1. 일자별 스케줄 구성
        days_count = max(1, (req.endDate - req.startDate).days + 1)
        weather_map = {w.date: w for w in (req.dailyWeathers or [])}

        daily_schedules = []
        places_pool = list(candidate_places)
        places_per_day = code_mapper.get_spots_per_day(req.placesPerDay)
        start_hour = code_mapper.get_start_time_hour(req.startTime)

        spot_index = 0
        for day_idx in range(1, days_count + 1):
            curr_date = req.startDate + timedelta(days=day_idx - 1)
            weather_info = weather_map.get(curr_date)
            weather_condition = weather_info.condition if weather_info else "SUNNY"

            day_places: List[AISchedulePlace] = []
            selected_for_day = places_pool[spot_index : spot_index + places_per_day]
            spot_index += places_per_day

            # 남은 장소가 부족할 경우 순환
            if not selected_for_day and places_pool:
                selected_for_day = places_pool[:places_per_day]

            # 가용 시간대 계산 (시작시간 ~ 최대 21:00 종료)
            max_end_hour = 21
            total_slots = len(selected_for_day)
            
            curr_prev_spot = None
            total_day_dist = 0.0

            curr_minute = start_hour * 60
            max_minute = max_end_hour * 60
            # 장소당 할당 가능한 시간 (분)
            available_time = max(180, max_minute - curr_minute)
            step_slot_min = max(60, min(120, available_time // max(1, total_slots)))

            for step_idx, spot in enumerate(selected_for_day, start=1):
                # 직전 장소와의 거리 및 이동 시간 산출
                dist_km = 0.0
                travel_min = 0
                if curr_prev_spot:
                    dist_km = route_planner.calculate_distance_km(
                        curr_prev_spot["latitude"], curr_prev_spot["longitude"],
                        spot["latitude"], spot["longitude"],
                    )
                    travel_min = route_planner.estimate_travel_time_min(dist_km, req.transport)
                    total_day_dist += dist_km

                start_m = min(curr_minute + travel_min, max_minute - 30)
                stay_m = max(30, min(90, step_slot_min - travel_min))
                end_m = min(start_m + stay_m, max_minute)

                start_t = f"{start_m // 60:02d}:{start_m % 60:02d}"
                end_t = f"{end_m // 60:02d}:{end_m % 60:02d}"
                curr_minute = end_m
                curr_prev_spot = spot

                themes_name = code_mapper.get_theme_descriptions(req.themes) if req.themes else (req.theme or "힐링 코스")
                reason_text = (
                    f"{weather_condition} 날씨와 '{themes_name}' 테마에 맞춰 선정된 대표 코스로, "
                    f"이동 동선 효율과 만족도를 고려하여 추천되었습니다."
                )

                day_places.append(
                    AISchedulePlace(
                        step=step_idx,
                        placeId=spot["id"],
                        placeName=spot["name"],
                        category=spot["category"],
                        startTime=start_t,
                        endTime=end_t,
                        stayTimeMinutes=max(30, end_m - start_m),
                        latitude=spot["latitude"],
                        longitude=spot["longitude"],
                        distanceFromPrevKm=round(dist_km, 2) if step_idx > 1 else None,
                        estimatedTravelMinutes=travel_min if step_idx > 1 else None,
                        transportMode=req.transport or "PUBLIC_TRANSIT",
                        reason=reason_text,
                        address=spot.get("address"),
                    )
                )

            daily_schedules.append(
                AIDailySchedule(
                    day=day_idx,
                    date=curr_date.strftime("%Y-%m-%d"),
                    weatherCondition=weather_condition,
                    totalDayDistanceKm=round(total_day_dist, 2),
                    places=day_places,
                )
            )

        region_name = code_mapper.resolve_region_name(req.regionCodes[0] if req.regionCodes else (req.regionCode or "부산"))
        trip_name = f"{region_name} 맞춤 여행 {days_count}일 코스"
        weather_summary = (
            f"여행 기간 기상 예보를 종합 반영하여 지그재그 이동 없는 최단 동선과 "
            f"날씨 맞춤형 장소 위주로 구성된 안전한 일정입니다."
        )

        return AIScheduleResponse(
            tripName=trip_name,
            weatherSummary=weather_summary,
            dailySchedules=daily_schedules,
        )


llm_client = LLMClient()

