import time
from typing import List, Dict, Any, Optional
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.travel import TravelSpot
from app.schemas.ai import (
    AIScheduleRequest,
    AIScheduleResponse,
    AIRescheduleRequest,
    AIRescheduleResponse,
    AISchedulePlace,
)
from app.core.logger import app_logger
from app.core.embedding import embedding_service
from app.core.route_planner import route_planner
from app.core.weather_advisor import weather_advisor
from app.core.code_mapper import code_mapper
from app.core.llm_client import llm_client
from app.schemas.ai import DailyWeatherInput


class AIScheduleService:
    """날씨·계절 기반 RAG + 동선 최적화 + LLM 일정 생성 및 재추천 통합 서비스 (AI.md 규격)"""

    async def generate_schedule(
        self,
        db: AsyncSession,
        req: AIScheduleRequest,
    ) -> AIScheduleResponse:
        """[1단계 RAG ➡️ 2단계 동선 최적화 ➡️ 3단계 LLM 일정 빌드] 파이프라인 실행"""
        
        # 0. 지역명 목록 정규화
        region_names = (
            code_mapper.resolve_region_names(req.regionCodes)
            if req.regionCodes
            else [code_mapper.resolve_region_name(req.regionCode or "부산")]
        )

        # ---------------------------------------------------------------------
        # [분기 처리] 복수 지역(2개 이상) 요청 시 전용 연계 로직으로 분기 (기존 로직 보존)
        # ---------------------------------------------------------------------
        if len(region_names) > 1:
            app_logger.info(f"🌐 [복수 지역 연계 모드 진입] 대상 지역: {region_names}")
            return await self._generate_multi_region_schedule(db, req, region_names)

        # ---------------------------------------------------------------------
        # [기존 단일 지역 파이프라인] - 기존 로직 그대로 유지
        # ---------------------------------------------------------------------
        raw_region = req.regionCodes[0] if req.regionCodes else (req.regionCode or "부산")
        region_name = region_names[0]
        companion_name, companion_tags = code_mapper.get_companion_info(
            req.companionType,
            req.travelerCount or req.personCount or 2
        )
        themes_text = code_mapper.get_theme_descriptions(req.themes) if req.themes else (req.theme or "힐링 미식")
        spots_per_day = code_mapper.get_spots_per_day(req.placesPerDay)

        app_logger.info(
            f"🚀 [단일 지역 일정 생성] region={region_name}(code={raw_region}), "
            f"period={req.startDate}~{req.endDate}, companion={companion_name}, themes={themes_text}"
        )


        # 0-1. 날씨 정보가 없을 경우 자체 계절/날씨 추론하여 보강 (02_명세: FE/BE에서 미입력 시 대비)
        if not req.dailyWeathers:
            travel_days = max(1, (req.endDate - req.startDate).days + 1)
            generated_weathers = []
            for d_idx in range(travel_days):
                curr_d = req.startDate + timedelta(days=d_idx)
                wb = weather_advisor.generate_weather_briefing(region_name, curr_d)
                generated_weathers.append(
                    DailyWeatherInput(
                        date=curr_d,
                        condition="RAIN" if "비" in wb["expected_weather"] else "SUNNY",
                        temp=20.0,
                        precipitationProbability=10,
                    )
                )
            req.dailyWeathers = generated_weathers

        # 1단계: RAG 기반 날씨·계절 시맨틱 장소 추출 (Retrieval)
        is_any_rain = any(
            "RAIN" in (w.condition or "").upper() or "비" in (w.condition or "")
            for w in (req.dailyWeathers or [])
        )

        # 시맨틱 검색 쿼리 빌드
        weather_keyword = "비 오는 날 실내 명소 및 아늑한 오션뷰 카페 복합문화공간" if is_any_rain else "맑은 날 즐기기 좋은 야외 명소와 힐링 산책로 감성 스팟"
        semantic_query = f"{region_name} {themes_text} {companion_name} {weather_keyword} 인기 명소 맛집 카페"
        
        query_vec = embedding_service.embed_text(semantic_query)
        cosine_dist = TravelSpot.embedding.cosine_distance(query_vec)
        cosine_sim = (1.0 - cosine_dist).label("similarity")

        # pgvector 유사도 검색
        stmt = (
            select(TravelSpot, cosine_sim)
            .where(TravelSpot.region.ilike(f"%{region_name}%"))
            .order_by(cosine_dist.asc())
            .limit(30)
        )
        res = await db.execute(stmt)
        candidate_rows = res.all()

        # 만약 지역에 매칭되는 데이터가 적으면 전체 대상 Fallback
        if not candidate_rows:
            app_logger.warning(f"'{region_name}' 등록 장소가 부족하여 전체 지역에서 유사 장소를 탐색합니다.")
            fallback_stmt = select(TravelSpot, cosine_sim).order_by(cosine_dist.asc()).limit(30)
            res = await db.execute(fallback_stmt)
            candidate_rows = res.all()

        if not candidate_rows:
            raise ValueError(f"'{region_name}' 관련 여행 스팟 데이터가 데이터베이스에 존재하지 않습니다.")

        # 후보군 추출 및 날씨/동행자 적합성 하이브리드 리랭킹 (AI.md 3.2)
        candidate_places = []
        for spot, sim in candidate_rows:
            meta = spot.spot_metadata or {}
            final_score = float(sim)

            # 1. 우천 시 실내 장소 가중치 부여 (+20%)
            is_indoor = (
                meta.get("is_indoor") is True
                or "실내" in spot.category
                or "카페" in spot.category
                or "비오는날_실내" in meta.get("weather_suitability", [])
            )
            if is_any_rain and is_indoor:
                final_score += 0.20

            # 2. 동행자 유형 매칭 가중치 (+15%)
            spot_companions = meta.get("companion_types", [])
            if any(tag in spot_companions for tag in companion_tags):
                final_score += 0.15

            # 3. 사용자 선택 테마 매칭 가중치 (+10%)
            spot_tags = meta.get("tags", [])
            if any(th in spot.category or any(th in t for t in spot_tags) for th in (req.themes or [])):
                final_score += 0.10

            candidate_places.append({
                "id": str(spot.id),
                "name": spot.name,
                "region": spot.region,
                "category": spot.category,
                "address": spot.address,
                "latitude": spot.latitude,
                "longitude": spot.longitude,
                "description": spot.description,
                "metadata": meta,
                "is_indoor": is_indoor,
                "similarity": float(sim),
                "score": round(final_score, 4),
            })

        # 하이브리드 점수 기준 정렬
        candidate_places.sort(key=lambda s: s["score"], reverse=True)

        app_logger.info(
            f"Top-{len(candidate_places)} 후보 장소 하이브리드 스코어링 완료 | "
            f"top_score={candidate_places[0]['score']}, is_any_rain={is_any_rain}"
        )


        # 2단계: 위경도 좌표 및 카테고리 제약조건(식사/카페/중복방지) 기반 동선 최적화 (AI.md 4.1)
        travel_days = max(1, (req.endDate - req.startDate).days + 1)
        daily_grouped = route_planner.optimize_category_aware_itinerary(
            spots=candidate_places,
            travel_days=travel_days,
            spots_per_day=spots_per_day,
        )


        # 1차 정렬된 후보군 플랫 리스트로 재구성 (순서 보장)
        ordered_candidates = [spot for day_spots in daily_grouped for spot in day_spots]
        # 만약 카테고리 슬롯에서 누락된 나머지 후보가 있다면 뒤쪽에 추가
        selected_ids = {s["id"] for s in ordered_candidates}
        for s in candidate_places:
            if s["id"] not in selected_ids:
                ordered_candidates.append(s)

        # 3단계: LLM 프롬프트 빌드 & 응답 파싱 및 환각/포맷오류 재요청
        final_schedule = await llm_client.generate_schedule_with_retry(
            req=req,
            candidate_places=ordered_candidates,
        )

        return final_schedule

    async def _generate_multi_region_schedule(
        self,
        db: AsyncSession,
        req: AIScheduleRequest,
        region_names: List[str],
    ) -> AIScheduleResponse:
        """복수 지역(2개 이상) 연계 여행 전용 파이프라인 (기존 단일 지역 로직과 분기 격리)"""
        travel_days = max(1, (req.endDate - req.startDate).days + 1)
        companion_name, companion_tags = code_mapper.get_companion_info(
            req.companionType,
            req.travelerCount or req.personCount or 2
        )
        themes_text = code_mapper.get_theme_descriptions(req.themes) if req.themes else (req.theme or "힐링 미식")
        spots_per_day = code_mapper.get_spots_per_day(req.placesPerDay)

        app_logger.info(
            f"🚀 [복수 지역 연계 파이프라인 시작] regions={region_names}, days={travel_days}, themes={themes_text}"
        )

        # 1. 일자별 지역 분할 매핑 (Day-Region Allocation)
        # 예: 3일 여행 & 2개 지역 (부산, 울산) -> Day 1: 부산, Day 2: 부산, Day 3: 울산
        day_region_map = {}
        for day_idx in range(1, travel_days + 1):
            r_idx = min(len(region_names) - 1, int((day_idx - 1) / travel_days * len(region_names)))
            day_region_map[day_idx] = region_names[r_idx]

        # 2. 날씨 정보 보강 (일자별 해당 지역 기준)
        if not req.dailyWeathers:
            generated_weathers = []
            for d_idx in range(travel_days):
                curr_d = req.startDate + timedelta(days=d_idx)
                curr_reg = day_region_map[d_idx + 1]
                wb = weather_advisor.generate_weather_briefing(curr_reg, curr_d)
                generated_weathers.append(
                    DailyWeatherInput(
                        date=curr_d,
                        condition="RAIN" if "비" in wb["expected_weather"] else "SUNNY",
                        temp=20.0,
                        precipitationProbability=10,
                    )
                )
            req.dailyWeathers = generated_weathers

        is_any_rain = any(
            "RAIN" in (w.condition or "").upper() or "비" in (w.condition or "")
            for w in (req.dailyWeathers or [])
        )

        # 3. 각 지역별 pgvector RAG 장소 추출
        all_candidate_places = []
        for reg in region_names:
            weather_keyword = "비 오는 날 실내 명소 및 카페" if is_any_rain else "맑은 날 즐기기 좋은 야외 명소와 힐링 스팟"
            semantic_query = f"{reg} {themes_text} {companion_name} {weather_keyword} 인기 명소 맛집 카페"
            
            query_vec = embedding_service.embed_text(semantic_query)
            cosine_dist = TravelSpot.embedding.cosine_distance(query_vec)
            cosine_sim = (1.0 - cosine_dist).label("similarity")

            stmt = (
                select(TravelSpot, cosine_sim)
                .where(TravelSpot.region.ilike(f"%{reg}%"))
                .order_by(cosine_dist.asc())
                .limit(20)
            )
            res = await db.execute(stmt)
            reg_rows = res.all()

            for spot, sim in reg_rows:
                meta = spot.spot_metadata or {}
                final_score = float(sim)
                is_indoor = (
                    meta.get("is_indoor") is True
                    or "실내" in spot.category
                    or "카페" in spot.category
                    or "비오는날_실내" in meta.get("weather_suitability", [])
                )
                if is_any_rain and is_indoor:
                    final_score += 0.20
                if any(tag in meta.get("companion_types", []) for tag in companion_tags):
                    final_score += 0.15

                all_candidate_places.append({
                    "id": str(spot.id),
                    "name": spot.name,
                    "region": spot.region,
                    "category": spot.category,
                    "address": spot.address,
                    "latitude": spot.latitude,
                    "longitude": spot.longitude,
                    "description": spot.description,
                    "metadata": meta,
                    "is_indoor": is_indoor,
                    "similarity": float(sim),
                    "score": round(final_score, 4),
                })

        # DB에 해당 지역 데이터가 부족할 경우 전체 Fallback
        if not all_candidate_places:
            app_logger.warning("지정된 복수 지역의 데이터가 부족하여 전체 지역에서 유사 장소를 추출합니다.")
            fallback_stmt = select(TravelSpot, cosine_sim).order_by(cosine_dist.asc()).limit(30)
            res = await db.execute(fallback_stmt)
            for spot, sim in res.all():
                all_candidate_places.append({
                    "id": str(spot.id), "name": spot.name, "region": spot.region, "category": spot.category,
                    "address": spot.address, "latitude": spot.latitude, "longitude": spot.longitude,
                    "description": spot.description, "metadata": spot.spot_metadata or {},
                    "score": float(sim), "similarity": float(sim), "is_indoor": False
                })

        # 4. 일자별 지역 슬롯팅 및 체이닝 동선 최적화
        daily_grouped = []
        used_ids = set()
        prev_day_last_spot = None

        for day_idx in range(1, travel_days + 1):
            assigned_region = day_region_map[day_idx]
            # 해당 일차에 배정된 지역의 후보군 우선 필터링
            reg_candidates = [
                s for s in all_candidate_places
                if assigned_region in s["region"] and s["id"] not in used_ids
            ]
            if not reg_candidates:
                reg_candidates = [s for s in all_candidate_places if s["id"] not in used_ids]

            day_plan_raw = route_planner.optimize_category_aware_itinerary(
                spots=reg_candidates,
                travel_days=1,
                spots_per_day=spots_per_day,
            )
            if day_plan_raw:
                day_spots = day_plan_raw[0]
                daily_grouped.append(day_spots)
                for s in day_spots:
                    used_ids.add(s["id"])
                prev_day_last_spot = day_spots[-1]

        ordered_candidates = [spot for day_spots in daily_grouped for spot in day_spots]
        for s in all_candidate_places:
            if s["id"] not in used_ids:
                ordered_candidates.append(s)

        # 5. LLM 일정 빌드 (복수 지역 연계 일정 생성)
        final_schedule = await llm_client.generate_schedule_with_retry(
            req=req,
            candidate_places=ordered_candidates,
        )

        return final_schedule

    async def reschedule(
        self,
        db: AsyncSession,
        req: AIRescheduleRequest,
    ) -> AIRescheduleResponse:
        """기상 악화(우천/폭설 등) 대응 실시간 대체 일정 재추천 (AI.md 8장)"""
        region_name = code_mapper.resolve_region_name(req.regionCode)
        app_logger.info(
            f"🌧️ [실시간 재추천 요청] region={region_name}(code={req.regionCode}), "
            f"pos=({req.currentLatitude}, {req.currentLongitude}), new_weather={req.newWeatherCondition}"
        )

        # 1. 변경된 날씨에 맞는 시맨틱 검색어 생성
        query_text = f"{region_name} 비 오는 날 실내 즐길거리 미술관 아쿠아리움 대형 오션뷰 카페 실내복합공간"
        query_vec = embedding_service.embed_text(query_text)
        cosine_dist = TravelSpot.embedding.cosine_distance(query_vec)

        # 2. 반경 필터링 및 유사도 검색
        stmt = (
            select(TravelSpot)
            .where(TravelSpot.region.ilike(f"%{region_name}%"))
            .order_by(cosine_dist.asc())
            .limit(25)
        )

        res = await db.execute(stmt)
        all_candidates = res.scalars().all()

        # 현재 위치 기준 반경 내 장소 필터링
        nearby_spots = []
        for s in all_candidates:
            dist = route_planner.calculate_distance_km(
                req.currentLatitude, req.currentLongitude,
                s.latitude, s.longitude
            )
            meta = s.spot_metadata or {}
            # 우천 시 실내 장소 우선
            is_indoor = meta.get("is_indoor", False) or "실내" in s.category or "카페" in s.category or "비오는날_실내" in meta.get("weather_suitability", [])

            if dist <= req.radiusKm or len(nearby_spots) < req.remainingStepsCount:
                nearby_spots.append({
                    "id": str(s.id),
                    "name": s.name,
                    "category": s.category,
                    "address": s.address,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "description": s.description,
                    "distance_km": dist,
                    "is_indoor": is_indoor,
                })

        # 실내 장소 우선 정렬 후 거리순
        nearby_spots.sort(key=lambda x: (not x["is_indoor"], x["distance_km"]))
        selected = nearby_spots[: req.remainingStepsCount]

        # 동선 정렬
        ordered_spots = route_planner.optimize_spot_order(selected)

        # 시간표 조립
        result_places: List[AISchedulePlace] = []
        start_hour = 14
        curr_dist_total = 0.0

        for idx, spot in enumerate(ordered_spots, start=1):
            start_str = f"{start_hour + idx - 1}:00"
            end_str = f"{start_hour + idx}:30"
            curr_dist_total += spot["distance_km"]

            result_places.append(
                AISchedulePlace(
                    step=idx,
                    placeId=spot["id"],
                    placeName=spot["name"],
                    category=spot["category"],
                    startTime=start_str,
                    endTime=end_str,
                    stayTimeMinutes=90,
                    latitude=spot["latitude"],
                    longitude=spot["longitude"],
                    reason=f"갑작스러운 {req.newWeatherCondition} 날씨에 안전하고 쾌적하게 머무를 수 있는 실내 명소로 선정되었습니다.",
                    address=spot.get("address"),
                )
            )

        return AIRescheduleResponse(
            message=f"갑작스러운 {req.newWeatherCondition} 예보에 따라 현재 위치 반경 {req.radiusKm}km 내 실내 대체 코스로 동선이 재조정되었습니다.",
            newCondition=req.newWeatherCondition,
            recommendedPlaces=result_places,
            totalDistanceKm=round(curr_dist_total, 2),
        )


ai_schedule_service = AIScheduleService()

