import time
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMAdvisor:
    """Ollama travel-llama3 모델 기반 맞춤형 여행 스토리 및 일정 생성기 (싱글톤)"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.chat_url = f"{self.base_url}/api/chat"
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SEC

    def _build_prompt(
        self,
        region: str,
        start_date: str,
        end_date: str,
        travel_days: int,
        person_count: int,
        companion_label: str,
        theme: str,
        transportation: str,
        spots: List[Dict[str, Any]],
        weather_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """벡터 DB 스팟 및 날씨 정보를 종합하여 LLM에 전달할 사용자 프롬프트 구성"""
        
        # 상위 스팟 메타데이터 정돈
        formatted_spots = []
        for rank, s in enumerate(spots[:8], start=1):
            meta = s.get("metadata") or {}
            formatted_spots.append({
                "rank": rank,
                "name": s.get("name"),
                "category": s.get("category"),
                "address": s.get("address"),
                "similarity_score": round(float(s.get("score", 0.0)), 4),
                "stay_duration_min": meta.get("estimated_stay_min", 90),
                "description": s.get("description"),
                "tags": meta.get("tags", []),
                "companion_types": meta.get("companion_types", []),
            })

        weather_text = ""
        if weather_info:
            weather_text = (
                f"- 예상 날씨: {weather_info.get('expected_weather', '맑음')} "
                f"({weather_info.get('expected_temperature', '적정 기온')})\n"
                f"- 계절/날씨 팁: {weather_info.get('travel_tip', '')}\n"
            )

        prompt = f"""[사용자 여행 요청 조건]
- 여행 지역: {region}
- 여행 기간: {start_date} ~ {end_date} ({travel_days}박 {travel_days+1 if travel_days > 1 else 1}일)
- 인원 및 동행: {person_count}인 ({companion_label})
- 여행 테마: {theme}
- 이동 수단: {transportation}
{weather_text}
[벡터 DB 시맨틱 검색 결과 (Top {len(formatted_spots)})]
{json.dumps(formatted_spots, indent=2, ensure_ascii=False)}

[작성 지침]
1. {travel_days}일 일정(Day 1부터)으로 나누어 오전, 점심, 오후, 저녁 시간대별 동선을 구성하세요.
2. 각 스팟마다 다음 항목을 포함하세요:
   - 추천 방문 시간대 및 권장 체류 시간
   - 여행 테마({theme}) 및 {companion_label} 관점에서의 장소 선정 이유
   - 맞춤형 여행 꿀팁 (포토존, 추천 메뉴, 일몰 포인트 등)
3. 전체 이동 동선 요약과 총평을 마지막에 친절하고 감성적인 한국어로 작성하세요.
4. 반드시 한국어로만 작성하세요.
"""
        return prompt

    async def generate_itinerary_story(
        self,
        region: str,
        start_date: str,
        end_date: str,
        travel_days: int,
        person_count: int,
        companion_label: str,
        theme: str,
        transportation: str,
        spots: List[Dict[str, Any]],
        weather_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """비동기 HTTP 통신으로 Ollama 서버에 질의하여 맞춤형 일정 스토리 생성"""
        
        prompt = self._build_prompt(
            region=region,
            start_date=start_date,
            end_date=end_date,
            travel_days=travel_days,
            person_count=person_count,
            companion_label=companion_label,
            theme=theme,
            transportation=transportation,
            spots=spots,
            weather_info=weather_info,
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.6,
                "top_p": 0.9,
            }
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(self.chat_url, json=payload)
                res.raise_for_status()
                res_json = res.json()

            elapsed = time.time() - start_time
            content = res_json.get("message", {}).get("content", "")
            eval_count = res_json.get("eval_count", 0)

            logger.info(
                f"[LLMAdvisor] 일정 생성 성공 (소요시간: {elapsed:.2f}s, 토큰: {eval_count})"
            )

            return {
                "model": self.model,
                "generation_time_sec": round(elapsed, 2),
                "content": content,
                "tokens": eval_count,
            }

        except httpx.ConnectError as e:
            logger.warning(f"[LLMAdvisor] Ollama 서버 연결 실패 ({self.chat_url}): {e}")
            return {
                "model": self.model,
                "generation_time_sec": round(time.time() - start_time, 2),
                "content": "AI 모델 서버(Ollama)에 일시적으로 연결할 수 없어 기본 추천 일정을 제공합니다.",
                "tokens": 0,
            }
        except httpx.TimeoutException as e:
            logger.warning(f"[LLMAdvisor] Ollama 서버 응답 시간 초과 ({self.timeout}s): {e}")
            return {
                "model": self.model,
                "generation_time_sec": round(time.time() - start_time, 2),
                "content": "AI 모델 응답 시간 초과로 기본 추천 일정을 제공합니다.",
                "tokens": 0,
            }
        except Exception as e:
            logger.error(f"[LLMAdvisor] Ollama 호출 중 예상치 못한 에러: {e}")
            return {
                "model": self.model,
                "generation_time_sec": round(time.time() - start_time, 2),
                "content": f"AI 일정 생성 중 오류가 발생했습니다: {str(e)}",
                "tokens": 0,
            }


llm_advisor = LLMAdvisor()

