import json
from typing import List, Dict, Any, Optional
from datetime import date

from app.schemas.ai import AIScheduleRequest, DailyWeatherInput
from app.core.code_mapper import code_mapper


class PromptBuilder:
    """AI.md 6장 및 02_요청 데이터 명세 초안 규격을 준수하는 프롬프트 생성기"""

    SYSTEM_PROMPT = (
        "당신은 대한민국 최고의 AI 여행 플래너 \"Trp Engine\"입니다.\n"
        "주어진 장소 후보군과 여행 조건, 당일 기상청 날씨/계절 정보를 종합 분석하여, "
        "여행자가 지치지 않고 날씨를 즐길 수 있는 최적의 시간대별 여행 일정을 설계해야 합니다.\n\n"
        "[작성 원칙]\n"
        "1. 반드시 전달받은 후보 장소 목록(Candidate Places) 내에서만 선택하십시오. (환각 금지)\n"
        "2. 날씨가 우천(RAIN)일 경우 반드시 실내 장소 및 비 풍경이 좋은 장소 위주로 배치하고, 추천 사유에 날씨 팁을 명시하십시오.\n"
        "3. 점심 시간(12:00~13:30)과 저녁 시간(18:00~19:30)에는 반드시 음식점이 배치되어야 하며, "
        "식사 직후에는 멀리 이동하지 않고 인근의 [카페/디저트] 또는 [산책/전시 등 컨텐츠]가 순서대로 자연스럽게 이어지도록 설계하십시오.\n"
        "4. 출력 형식은 다른 설명(인사말, 마크다운 등) 없이 반드시 순수한 JSON 형식만 반환하십시오.\n\n"
        "[JSON 스키마 규격]\n"
        "{\n"
        '  "tripName": "비 오는 가을 부산 감성 힐링 1일 코스",\n'
        '  "weatherSummary": "강수확률 80% 우천 예보로 전 일정 실내 문화 및 오션뷰 카페 중심 구성",\n'
        '  "dailySchedules": [\n'
        "    {\n"
        '      "day": 1,\n'
        '      "date": "2026-10-25",\n'
        '      "weatherCondition": "RAIN",\n'
        '      "places": [\n'
        "        {\n"
        '          "step": 1,\n'
        '          "placeId": 1024,\n'
        '          "placeName": "장소명",\n'
        '          "category": "INDOOR_EXHIBITION",\n'
        '          "startTime": "10:30",\n'
        '          "endTime": "12:30",\n'
        '          "stayTimeMinutes": 120,\n'
        '          "latitude": 35.1593,\n'
        '          "longitude": 129.1611,\n'
        '          "reason": "오전 비 예보에 맞춰 쾌적하게 관람할 수 있는 실내 코스로 선정했습니다."\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    @classmethod
    def build_user_prompt(
        cls,
        req: AIScheduleRequest,
        candidate_places: List[Dict[str, Any]],
        error_feedback: Optional[str] = None,
    ) -> str:
        """User Prompt 빌더: 날씨, 여행 조건, 후보 장소 주입 및 오류 피드백 반영"""
        
        # 1. 02_요청 데이터 명세 초안 코드값 해석
        region_name = code_mapper.resolve_region_name(req.regionCodes[0] if req.regionCodes else (req.regionCode or "부산"))
        companion_name, companion_tags = code_mapper.get_companion_info(
            req.companionType,
            req.travelerCount or req.personCount or 2
        )
        transport_desc = code_mapper.TRANSPORT_MAP.get(req.transport or req.transportation or "PUBLIC_TRANSIT", req.transport or "대중교통")
        themes_desc = code_mapper.get_theme_descriptions(req.themes) if req.themes else (req.theme or "힐링/명소")
        spots_count = code_mapper.get_spots_per_day(req.placesPerDay)
        start_time_str = code_mapper.START_TIME_MAP.get(req.startTime or "NORMAL", "10:00")

        # 2. 날씨 정보 포매팅
        weather_desc_lines = []
        if req.dailyWeathers:
            for w in req.dailyWeathers:
                temp_str = f"{w.temp}℃" if w.temp is not None else "평년기온"
                pop_str = f", 강수확률 {w.precipitationProbability}%" if w.precipitationProbability is not None else ""
                weather_desc_lines.append(f"- {w.date}: {w.condition} (기온: {temp_str}{pop_str})")
        else:
            weather_desc_lines.append("- 예보 데이터 없음 (쾌적한 일반 날씨 기준)")

        # 3. 후보 장소 목록 포매팅 (LLM이 환각 없이 고를 수 있도록 명확히 전달)
        candidates_formatted = []
        for idx, p in enumerate(candidate_places, start=1):
            meta = p.get("metadata", {})
            indoor_str = "실내" if meta.get("is_indoor") or "실내" in meta.get("weather_suitability", []) else "야외"
            candidates_formatted.append(
                f"{idx}. ID: {p['id']} | 이름: {p['name']} | 카테고리: {p['category']} | 유형: {indoor_str} | "
                f"좌표: ({p['latitude']}, {p['longitude']}) | 설명: {p.get('description', '')[:100]}"
            )

        prompt_parts = [
            f"### [여행 요청 조건 (02_요청 데이터 명세 기반)]",
            f"- 대상 지역: {region_name} (입력코드: {req.regionCodes or req.regionCode})",
            f"- 여행 기간: {req.startDate} ~ {req.endDate}",
            f"- 동행 유형: {companion_name} ({req.travelerCount or req.personCount or 2}인, 태그: {', '.join(companion_tags)})",
            f"- 이동 수단: {transport_desc}",
            f"- 여행 테마: {themes_desc}",
            f"- 하루 일정 밀도: 하루 약 {spots_count}곳 권장 ({req.placesPerDay or 'NORMAL'})",
            f"- 첫 일정 시작 시각: {start_time_str}부터 시작하여 21:00경 종료 ({req.startTime or 'NORMAL'})",
            "",
            f"### [당일 기상청 날씨/예보 정보]",
            "\n".join(weather_desc_lines),
            "",
            f"### [선택 가능한 후보 장소 목록 (Candidate Places)]",
            "※ 주의: 아래 목록에 명시된 장소만 일정에 포함해야 합니다. 목록에 없는 가상의 장소를 추가하면 시스템 오류가 발생합니다.",
            "\n".join(candidates_formatted),
        ]

        # 3. 예외 재시도 피드백이 있을 경우 주입
        if error_feedback:
            prompt_parts.extend([
                "",
                "🚨 [긴급 보정 요청 - 이전 응답 오류 피드백]",
                f"직전 응답에서 다음과 같은 오류가 검출되었습니다:",
                f"-> {error_feedback}",
                "위 오류를 반드시 수정하여, 어떤 추가 부연 설명이나 마크다운 코드블록 없이 오직 유효한 순수 JSON만 재출력하십시오.",
            ])

        return "\n".join(prompt_parts)


prompt_builder = PromptBuilder()

