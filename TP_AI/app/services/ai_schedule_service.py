import time
import math
from typing import List, Dict, Any, Optional
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.schemas.ai import (
    AIScheduleRequest,
    AIScheduleResponse,
    AIRescheduleRequest,
    AIRescheduleResponse,
    AISchedulePlace,
    DailyWeatherInput,
)
from app.core.logger import app_logger
from app.core.route_planner import route_planner
from app.core.weather_advisor import weather_advisor
from app.core.code_mapper import code_mapper
from app.core.llm_client import llm_client


# TourAPI 지역코드 및 시도/시군구 계층 구조 반영 tour_places 조회 쿼리 (is_deleted = FALSE 필터링)
TOUR_PLACES_QUERY = text("""
WITH sido AS (
  SELECT DISTINCT COALESCE(s.region_code, g.parent_code) AS code
  FROM unnest(CAST(:codes AS text[])) AS c(code)
  LEFT JOIN region s ON s.level = 'SIDO' AND (s.tour_area_code = c.code OR s.region_code = c.code)
  LEFT JOIN region g ON s.region_code IS NULL AND g.level = 'SIGUNGU' AND g.tour_area_code = c.code
)
SELECT p.id, p.name, p.category, p.latitude, p.longitude, p.is_indoor,
       d.open_time, d.close_time, d.closed_weekdays, d.business_hours, d.holiday_info
FROM tour_places p
LEFT JOIN tour_place_details d ON d.place_id = p.id
WHERE p.is_deleted = FALSE
  AND p.region_code IN (SELECT code FROM sido
                        UNION SELECT region_code FROM region WHERE parent_code IN (SELECT code FROM sido));
""")


class AIScheduleService:
    """날씨·계절 기반 룰 선정 + 카테고리/동선 최적화 + LLM 일정 생성 및 재추천 통합 서비스 (AI.md 7.1 & tour_db 규격)"""

    async def generate_schedule(
        self,
        db: AsyncSession,
        req: AIScheduleRequest,
    ) -> AIScheduleResponse:
        """[1단계 후보 선정 ➡️ 2단계 카테고리/동선 최적화 ➡️ 3단계 LLM 일정 빌드] 파이프라인 실행"""

        # 0. 지역 코드 정규화 (:codes 에 주입)
        codes: List[str] = []
        if req.regionCodes:
            codes = [str(c).strip() for c in req.regionCodes if str(c).strip()]
        elif req.regionCode:
            codes = [str(req.regionCode).strip()]
        if not codes:
            codes = ["6"]  # 기본값: 부산

        primary_region = code_mapper.resolve_region_name(codes[0])
        travel_days = max(1, (req.endDate - req.startDate).days + 1)
        companion_name, companion_tags = code_mapper.get_companion_info(
            req.companionType,
            req.travelerCount or req.personCount or 2,
        )
        themes_text = code_mapper.get_theme_descriptions(req.themes) if req.themes else (req.theme or "힐링 미식")
        spots_per_day = code_mapper.get_spots_per_day(req.placesPerDay)

        app_logger.info(
            f"🚀 [일정 생성 요청] regionCodes={codes}(primary={primary_region}), "
            f"period={req.startDate}~{req.endDate}({travel_days}일), companion={companion_name}, themes={themes_text}"
        )

        # 1. 날씨 정보 처리 (BE 전달값 우선 사용, 없으면 DB weather_forecasts 조회 없이 계절 기반 Fallback 추정)
        if not req.dailyWeathers:
            generated_weathers = []
            for d_idx in range(travel_days):
                curr_d = req.startDate + timedelta(days=d_idx)
                wb = weather_advisor.generate_weather_briefing(primary_region, curr_d)
                generated_weathers.append(
                    DailyWeatherInput(
                        date=curr_d,
                        condition="RAIN" if "비" in wb.get("expected_weather", "") else "SUNNY",
                        temp=float(wb.get("avg_temp", 20.0)),
                        precipitationProbability=70 if "비" in wb.get("expected_weather", "") else 10,
                    )
                )
            req.dailyWeathers = generated_weathers

        is_any_rain = any(
            "RAIN" in (w.condition or "").upper() or "비" in (w.condition or "")
            for w in (req.dailyWeathers or [])
        )

        # 2. tour_db.tour_places 계층 쿼리 실행 (tp_ai 읽기 전용 권한 준수)
        res = await db.execute(TOUR_PLACES_QUERY, {"codes": codes})
        rows = res.mappings().all()

        if not rows:
            app_logger.warning(f"⚠️ 지역 코드 {codes}에 해당하는 장소가 없어 기본 지역('6' 부산)으로 대체 조회합니다.")
            res = await db.execute(TOUR_PLACES_QUERY, {"codes": ["6"]})
            rows = res.mappings().all()

        if not rows:
            raise ValueError(f"'{codes}' 관련 여행 스팟 데이터가 tour_places에 존재하지 않습니다.")

        app_logger.info(f"📍 tour_places 조회 성공: 총 {len(rows)}개 장소 로드 완료 (is_any_rain={is_any_rain})")

        # 3. 임시 룰 기반 후보 선정 및 스코어링 (tour_embeddings 생성 전 단계)
        # 점심·저녁: RESTAURANT, 카페: CAFE (AI.md 6.1) 보장
        user_themes = [t.upper() for t in (req.themes or [])]
        theme_cat_map = {
            "FOOD": "RESTAURANT",
            "CAFE": "CAFE",
            "NATURE": "TOUR_SPOT",
            "HEALING": "TOUR_SPOT",
            "HISTORY_CULTURE": "CULTURE",
            "ACTIVITY": "LEISURE",
            "SHOPPING": "SHOPPING",
            "FESTIVAL": "FESTIVAL",
        }
        preferred_categories = {theme_cat_map[th] for th in user_themes if th in theme_cat_map}

        start_lat = float(req.startLatitude) if req.startLatitude is not None else None
        start_lon = float(req.startLongitude) if req.startLongitude is not None else None

        scored_spots = []
        for r in rows:
            cat = str(r["category"] or "").strip().upper()
            if cat == "ACCOMMODATION":
                continue  # 일정 방문 장소 풀에서 숙소는 제외

            lat = float(r["latitude"]) if r["latitude"] is not None else 0.0
            lon = float(r["longitude"]) if r["longitude"] is not None else 0.0
            is_indoor = bool(r["is_indoor"])

            # 기본 점수 산정
            score = 1.0

            # 날씨 가중치: 비 오는 날 실내(+0.30), 비 오는 날 야외 감점(-0.15)
            if is_any_rain:
                score += 0.30 if is_indoor else -0.15

            # 테마 매칭 가중치 (+0.25)
            if cat in preferred_categories:
                score += 0.25

            # 운영 시간 등 상세 정보 구비 가중치 (+0.05)
            if r["open_time"] or r["business_hours"]:
                score += 0.05

            # 거점 앵커링 인접 가중치
            if start_lat is not None and start_lon is not None and lat and lon:
                dist = route_planner.calculate_distance_km(start_lat, start_lon, lat, lon)
                score *= 1.0 / (1.0 + (dist * 0.04))

            scored_spots.append({
                "id": int(r["id"]),
                "name": r["name"],
                "category": cat,
                "latitude": lat,
                "longitude": lon,
                "is_indoor": is_indoor,
                "description": f"{r['name']} ({cat})",
                "open_time": str(r["open_time"]) if r["open_time"] else None,
                "close_time": str(r["close_time"]) if r["close_time"] else None,
                "business_hours": r["business_hours"],
                "score": round(score, 4),
                "metadata": {
                    "is_indoor": is_indoor,
                    "category": cat,
                },
            })

        # 카테고리별 분할
        restaurants = [s for s in scored_spots if s["category"] == "RESTAURANT"]
        cafes = [s for s in scored_spots if s["category"] == "CAFE"]
        contents = [s for s in scored_spots if s["category"] not in ("RESTAURANT", "CAFE")]

        restaurants.sort(key=lambda s: s["score"], reverse=True)
        cafes.sort(key=lambda s: s["score"], reverse=True)
        contents.sort(key=lambda s: s["score"], reverse=True)

        # 식사/카페/명소별 여유 있는 슬롯 확보
        n_rest = max(6, travel_days * 3)
        n_cafe = max(4, travel_days * 2)
        n_content = max(8, travel_days * 4)

        candidate_pool = restaurants[:n_rest] + cafes[:n_cafe] + contents[:n_content]
        if not candidate_pool:
            candidate_pool = scored_spots[:30]

        app_logger.info(
            f"📊 후보 장소 풀 구성 완료: 총 {len(candidate_pool)}개 "
            f"(식당 {len(restaurants[:n_rest])}, 카페 {len(cafes[:n_cafe])}, 컨텐츠 {len(contents[:n_content])})"
        )

        # 4. 카테고리 제약조건 및 동선 최적화 (AI.md 4.1)
        start_anchor = None
        if start_lat is not None and start_lon is not None:
            start_anchor = {
                "name": req.startLocationName or "시작 거점",
                "latitude": start_lat,
                "longitude": start_lon,
            }

        daily_grouped = route_planner.optimize_category_aware_itinerary(
            spots=candidate_pool,
            travel_days=travel_days,
            spots_per_day=spots_per_day,
            start_anchor=start_anchor,
        )

        # 순서 보장된 후보군 재배치 및 토큰 다이어트 최적화
        ordered_candidates = [spot for day_spots in daily_grouped for spot in day_spots]
        selected_ids = {s["id"] for s in ordered_candidates}
        for s in candidate_pool:
            if s["id"] not in selected_ids:
                ordered_candidates.append(s)

        max_prompt_candidates = min(len(ordered_candidates), (travel_days * spots_per_day) + 4)
        compressed_candidates = ordered_candidates[:max_prompt_candidates]

        # 5. LLM 프롬프트 빌드 & 응답 파싱 및 자체 복구 (Self-Correction / Fallback)
        final_schedule = await llm_client.generate_schedule_with_retry(
            req=req,
            candidate_places=compressed_candidates,
        )

        return final_schedule

    async def reschedule(
        self,
        db: AsyncSession,
        req: AIRescheduleRequest,
    ) -> AIRescheduleResponse:
        """기상 악화(우천/폭설 등) 대응 실시간 대체 일정 재추천 (AI.md 8장 - tour_places 연동)"""
        app_logger.info(
            f"🌧️ [실시간 재추천 요청] regionCode={req.regionCode}, "
            f"pos=({req.currentLatitude}, {req.currentLongitude}), new_weather={req.newWeatherCondition}"
        )

        # 현재 위치 기준 반경 경계 박스 계산 (위도 1도 ~ 111km, 경도 1도 ~ 88km)
        lat_delta = (req.radiusKm / 111.0) * 1.5
        lon_delta = (req.radiusKm / 88.0) * 1.5
        min_lat = req.currentLatitude - lat_delta
        max_lat = req.currentLatitude + lat_delta
        min_lon = req.currentLongitude - lon_delta
        max_lon = req.currentLongitude + lon_delta

        query = text("""
        SELECT p.id, p.name, p.category, p.latitude, p.longitude, p.is_indoor
        FROM tour_places p
        WHERE p.is_deleted = FALSE
          AND p.category != 'ACCOMMODATION'
          AND p.latitude BETWEEN :min_lat AND :max_lat
          AND p.longitude BETWEEN :min_lon AND :max_lon
        LIMIT 100;
        """)
        res = await db.execute(query, {
            "min_lat": min_lat, "max_lat": max_lat,
            "min_lon": min_lon, "max_lon": max_lon,
        })
        rows = res.mappings().all()

        nearby_spots = []
        is_rain = "RAIN" in (req.newWeatherCondition or "").upper() or "비" in (req.newWeatherCondition or "")

        for r in rows:
            lat = float(r["latitude"]) if r["latitude"] is not None else 0.0
            lon = float(r["longitude"]) if r["longitude"] is not None else 0.0
            dist = route_planner.calculate_distance_km(
                req.currentLatitude, req.currentLongitude, lat, lon
            )
            is_indoor = bool(r["is_indoor"]) or r["category"] == "CAFE"

            if dist <= req.radiusKm or len(nearby_spots) < req.remainingStepsCount:
                nearby_spots.append({
                    "id": int(r["id"]),
                    "name": r["name"],
                    "category": r["category"],
                    "latitude": lat,
                    "longitude": lon,
                    "distance_km": dist,
                    "is_indoor": is_indoor,
                })

        # 우천 시 실내 우선 정렬 후 거리순
        if is_rain:
            nearby_spots.sort(key=lambda x: (not x["is_indoor"], x["distance_km"]))
        else:
            nearby_spots.sort(key=lambda x: x["distance_km"])

        selected = nearby_spots[: req.remainingStepsCount]
        if not selected and rows:
            fallback_spots = [{
                "id": int(r["id"]),
                "name": r["name"],
                "category": r["category"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "distance_km": route_planner.calculate_distance_km(
                    req.currentLatitude, req.currentLongitude, float(r["latitude"]), float(r["longitude"])
                ),
                "is_indoor": bool(r["is_indoor"]),
            } for r in rows]
            fallback_spots.sort(key=lambda x: x["distance_km"])
            selected = fallback_spots[: req.remainingStepsCount]

        ordered_spots = route_planner.optimize_spot_order(selected)

        result_places: List[AISchedulePlace] = []
        curr_lat = req.currentLatitude
        curr_lon = req.currentLongitude
        curr_dist_total = 0.0

        curr_time_min = 14 * 60
        max_end_time_min = 21 * 60

        for idx, spot in enumerate(ordered_spots, start=1):
            leg_dist = route_planner.calculate_distance_km(
                curr_lat, curr_lon, spot["latitude"], spot["longitude"]
            )
            curr_dist_total += leg_dist
            travel_min = route_planner.estimate_travel_time_min(leg_dist)

            start_min = min(curr_time_min + travel_min, max_end_time_min - 30)
            stay_min = 90
            end_min = min(start_min + stay_min, max_end_time_min)
            actual_stay = max(30, end_min - start_min)

            start_str = f"{start_min // 60:02d}:{start_min % 60:02d}"
            end_str = f"{end_min // 60:02d}:{end_min % 60:02d}"

            result_places.append(
                AISchedulePlace(
                    step=idx,
                    placeId=spot["id"],
                    placeName=spot["name"],
                    category=spot["category"],
                    startTime=start_str,
                    endTime=end_str,
                    stayTimeMinutes=actual_stay,
                    latitude=spot["latitude"],
                    longitude=spot["longitude"],
                    distanceFromPrevKm=round(leg_dist, 2),
                    estimatedTravelMinutes=travel_min,
                    reason=f"갑작스러운 {req.newWeatherCondition} 날씨에 안전하고 쾌적하게 머무를 수 있는 {'실내 ' if spot['is_indoor'] else ''}명소로 선정되었습니다.",
                )
            )

            curr_lat = spot["latitude"]
            curr_lon = spot["longitude"]
            curr_time_min = end_min

        return AIRescheduleResponse(
            message=f"갑작스러운 {req.newWeatherCondition} 예보에 따라 현재 위치 반경 {req.radiusKm}km 내 대체 코스로 동선이 재조정되었습니다.",
            newCondition=req.newWeatherCondition,
            recommendedPlaces=result_places,
            totalDistanceKm=round(curr_dist_total, 2),
        )


ai_schedule_service = AIScheduleService()
