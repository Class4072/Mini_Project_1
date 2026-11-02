from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import timedelta
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_

from app.models.travel import TravelSpot
from app.schemas.travel import (
    TravelSpotCreate,
    BulkTravelSpotCreate,
    TravelSpotResponse,
    TravelRecommendRequest,
    TravelRecommendResponse,
    DestinationSummary,
    WeatherSummary,
    ItineraryDay,
    RouteStep,
)
from app.core.embedding import embedding_service
from app.core.route_planner import route_planner
from app.core.weather_advisor import weather_advisor


class TravelService:
    """날짜, 인원, 지역 조건 기반 날씨 분석, 지역 내 명소/놀거리 추천 및 경로 최적화 서비스"""

    def _build_embedding_text(self, spot_in: TravelSpotCreate) -> str:
        """장소명, 카테고리, 지역, 태그, 설명을 통합하여 풍부한 임베딩 텍스트 구성"""
        meta = spot_in.metadata or {}
        tags_str = ", ".join(meta.get("tags", []))
        companions = ", ".join(meta.get("companion_types", []))
        weather = ", ".join(meta.get("weather_suitability", []))
        
        parts = [
            f"장소명: {spot_in.name}",
            f"지역: {spot_in.region}",
            f"카테고리: {spot_in.category}",
            f"설명: {spot_in.description}",
        ]
        if tags_str:
            parts.append(f"태그: {tags_str}")
        if companions:
            parts.append(f"동행자: {companions}")
        if weather:
            parts.append(f"날씨/계절: {weather}")
            
        return " | ".join(parts)

    def _infer_companion_type(self, person_count: int) -> Tuple[str, List[str]]:
        """인원 수에 따른 동행자 그룹 명칭 및 매칭 태그 추론"""
        if person_count == 1:
            return "혼자 힐링 여행 (1인)", ["혼자"]
        elif person_count == 2:
            return "커플 / 2인 친구 여행", ["커플", "친구"]
        elif 3 <= person_count <= 4:
            return "가족 / 3~4인 친구 여행", ["가족", "친구"]
        else:
            return f"단체 / 대가족 여행 ({person_count}인)", ["가족", "친구"]

    async def create_spot(
        self,
        db: AsyncSession,
        spot_in: TravelSpotCreate,
    ) -> TravelSpotResponse:
        """단건 여행 스팟 등록 및 768차원 임베딩 생성"""
        emb_text = self._build_embedding_text(spot_in)
        vector = embedding_service.embed_text(emb_text)

        db_spot = TravelSpot(
            name=spot_in.name,
            region=spot_in.region,
            address=spot_in.address,
            category=spot_in.category,
            latitude=spot_in.latitude,
            longitude=spot_in.longitude,
            description=spot_in.description,
            spot_metadata=spot_in.metadata or {},
            embedding=vector,
        )
        db.add(db_spot)
        await db.commit()
        await db.refresh(db_spot)

        return self._to_response(db_spot)

    async def create_bulk_spots(
        self,
        db: AsyncSession,
        bulk_in: BulkTravelSpotCreate,
    ) -> List[TravelSpotResponse]:
        """여러 여행 스팟을 일괄 등록하고 배치 단위로 임베딩 인퍼런스 수행"""
        if not bulk_in.spots:
            return []

        emb_texts = [self._build_embedding_text(s) for s in bulk_in.spots]
        vectors = embedding_service.embed_batch(emb_texts)

        db_spots = []
        for s_in, vec in zip(bulk_in.spots, vectors):
            spot = TravelSpot(
                name=s_in.name,
                region=s_in.region,
                address=s_in.address,
                category=s_in.category,
                latitude=s_in.latitude,
                longitude=s_in.longitude,
                description=s_in.description,
                spot_metadata=s_in.metadata or {},
                embedding=vec,
            )
            db.add(spot)
            db_spots.append(spot)

        await db.commit()
        for s in db_spots:
            await db.refresh(s)

        return [self._to_response(s) for s in db_spots]

    async def get_spot(self, db: AsyncSession, spot_id: UUID) -> Optional[TravelSpotResponse]:
        """스팟 단건 조회"""
        stmt = select(TravelSpot).where(TravelSpot.id == spot_id)
        res = await db.execute(stmt)
        spot = res.scalar_one_or_none()
        return self._to_response(spot) if spot else None

    async def list_spots(
        self,
        db: AsyncSession,
        region: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[int, List[TravelSpotResponse]]:
        """스팟 목록 및 필터링 페이징 조회"""
        base_query = select(TravelSpot)
        count_query = select(func.count(TravelSpot.id))

        filters = []
        if region:
            filters.append(TravelSpot.region.ilike(f"%{region}%"))
        if category:
            filters.append(TravelSpot.category == category)

        if filters:
            base_query = base_query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total = (await db.execute(count_query)).scalar() or 0
        res = await db.execute(base_query.order_by(TravelSpot.created_at.desc()).offset(skip).limit(limit))
        spots = res.scalars().all()

        return total, [self._to_response(s) for s in spots]

    async def delete_spot(self, db: AsyncSession, spot_id: UUID) -> bool:
        """스팟 삭제"""
        stmt = select(TravelSpot).where(TravelSpot.id == spot_id)
        res = await db.execute(stmt)
        spot = res.scalar_one_or_none()
        if not spot:
            return False
        await db.delete(spot)
        await db.commit()
        return True

    async def search_spots(
        self,
        db: AsyncSession,
        query: str,
        region: Optional[str] = None,
        top_k: int = 10,
        use_hybrid: bool = True,
    ) -> List[Dict[str, Any]]:
        """장소 시맨틱 벡터 검색"""
        query_vec = embedding_service.embed_text(query)
        cosine_dist = TravelSpot.embedding.cosine_distance(query_vec)
        cosine_sim = (1.0 - cosine_dist).label("similarity")

        stmt = select(TravelSpot, cosine_sim)
        if region:
            stmt = stmt.where(TravelSpot.region.ilike(f"%{region}%"))

        stmt = stmt.order_by(cosine_dist.asc()).limit(top_k)
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for rank, (spot, sim) in enumerate(rows, start=1):
            results.append({
                "rank": rank,
                "spot": self._to_response(spot),
                "similarity_score": round(float(sim), 4),
            })
        return results

    async def recommend_travel(
        self,
        db: AsyncSession,
        req: TravelRecommendRequest,
    ) -> TravelRecommendResponse:
        """[날짜 + 인원 + 지역] 조건 기반 날씨 분석, 지역 내 놀거리/명소 추천 및 최단 이동 경로 리턴"""
        
        # 1. 여행 기간 계산
        travel_days = 1
        if req.end_date and req.end_date >= req.start_date:
            travel_days = min(7, (req.end_date - req.start_date).days + 1)

        # 2. 인원 수에 따른 동행 그룹 명칭 및 태그 추출
        companion_label, companion_tags = self._infer_companion_type(req.person_count)

        # 3. 자연어 검색 쿼리 구성 & 768차원 임베딩 생성
        season_key = weather_advisor.get_season(req.start_date)
        season_name = weather_advisor.SEASON_INFO[season_key]["name"]

        if req.theme_or_keyword:
            search_prompt = f"{req.region} {req.theme_or_keyword} {season_name} {companion_label} 추천 명소 놀거리 맛집 카페"
        else:
            search_prompt = f"{req.region} 대표 명소 관광지 놀거리 힐링 감성 카페 맛집 {season_name} {companion_label} 추천 코스"

        query_vec = embedding_service.embed_text(search_prompt)

        # 4. 해당 지역 내 후보 스팟 조회 (pgvector 코사인 유사도)
        cosine_dist = TravelSpot.embedding.cosine_distance(query_vec)
        cosine_sim = (1.0 - cosine_dist).label("similarity")

        stmt = (
            select(TravelSpot, cosine_sim)
            .where(TravelSpot.region.ilike(f"%{req.region}%"))
            .order_by(cosine_dist.asc())
            .limit(30)
        )
        res = await db.execute(stmt)
        candidate_rows = res.all()

        # 만약 해당 지역으로 등록된 스팟이 없으면 전체에서 유사 지역 검색 (Fallback)
        matched_region = req.region
        if not candidate_rows:
            fallback_stmt = select(TravelSpot, cosine_sim).order_by(cosine_dist.asc()).limit(30)
            res = await db.execute(fallback_stmt)
            candidate_rows = res.all()
            if candidate_rows:
                matched_region = candidate_rows[0][0].region
            else:
                raise ValueError(f"'{req.region}' 지역에 등록된 여행 스팟 데이터가 없습니다. 먼저 여행지 데이터를 등록해 주세요.")

        # 5. 스팟별 동행자/계절 적합성 가중치 부여
        scored_spots = []
        for spot, sim in candidate_rows:
            meta = spot.spot_metadata or {}
            final_score = float(sim)

            # 동행자 유형 매칭 가중치 (+15%)
            spot_companions = meta.get("companion_types", [])
            if any(tag in spot_companions for tag in companion_tags):
                final_score += 0.15

            # 계절 적합도 매칭 가중치 (+10%)
            spot_seasons = meta.get("best_seasons", [])
            if season_name in spot_seasons or "사계절" in spot_seasons:
                final_score += 0.10

            scored_spots.append({
                "id": spot.id,
                "name": spot.name,
                "region": spot.region,
                "category": spot.category,
                "address": spot.address,
                "latitude": spot.latitude,
                "longitude": spot.longitude,
                "description": spot.description,
                "metadata": meta,
                "score": final_score,
            })

        # 점수 순으로 정렬
        scored_spots.sort(key=lambda s: s["score"], reverse=True)

        # 6. 최적 이동 동선 및 일자별 일정 생성
        itinerary_raw = route_planner.build_itinerary(
            spots=scored_spots,
            travel_days=travel_days,
            spots_per_day=req.spots_per_day,
        )

        # 7. 날짜별 날씨 분석 정보 생성
        weather_info = weather_advisor.generate_weather_briefing(
            region=matched_region,
            target_date=req.start_date,
            weather_preference=None,
        )

        # 8. 일자별 실제 날짜 매핑 및 응답 구성
        itinerary = []
        for day_idx, d in enumerate(itinerary_raw):
            day_date = req.start_date + timedelta(days=day_idx)
            itinerary.append(
                ItineraryDay(
                    day=d["day"],
                    date=day_date.strftime("%Y-%m-%d"),
                    title=f"Day {d['day']} {matched_region} 핵심 명소 & 놀거리 코스",
                    total_spots=d["total_spots"],
                    total_distance_km=d["total_distance_km"],
                    total_travel_time_min=d["total_travel_time_min"],
                    routes=[
                        RouteStep(
                            order=r["order"],
                            spot_id=r["spot_id"],
                            name=r["name"],
                            category=r["category"],
                            address=r.get("address"),
                            latitude=r["latitude"],
                            longitude=r["longitude"],
                            description=r["description"],
                            stay_duration_min=r["stay_duration_min"],
                            distance_from_prev_km=r["distance_from_prev_km"],
                            estimated_travel_min=r["estimated_travel_min"],
                            tags=r.get("tags", []),
                        )
                        for r in d["routes"]
                    ],
                )
            )

        total_spots_count = sum(day.total_spots for day in itinerary)
        total_itinerary_distance = round(sum(day.total_distance_km for day in itinerary), 2)

        theme_text = req.theme_or_keyword or f"{matched_region} {travel_days}박 {travel_days+1 if travel_days > 1 else 1}일 추천 여행"

        destination_summary = DestinationSummary(
            requested_region=req.region,
            theme=theme_text,
            overview=f"{matched_region} 지역에서 {companion_label}에 어울리는 대표 명소, 힐링 스팟 및 감성 카페를 연결한 맞춤형 코스입니다.",
            companion_group=companion_label,
        )

        weather_summary = WeatherSummary(
            target_date=weather_info["target_date"],
            region=matched_region,
            season=weather_info["season"],
            expected_weather=weather_info["expected_weather"],
            expected_temperature=weather_info["expected_temperature"],
            travel_tip=weather_info["travel_tip"],
        )

        return TravelRecommendResponse(
            request_summary={
                "region": req.region,
                "start_date": str(req.start_date),
                "end_date": str(req.end_date) if req.end_date else str(req.start_date),
                "person_count": req.person_count,
                "theme_or_keyword": req.theme_or_keyword,
                "spots_per_day": req.spots_per_day,
            },
            destination_summary=destination_summary,
            weather_summary=weather_summary,
            itinerary=itinerary,
            total_days=len(itinerary),
            total_spots_count=total_spots_count,
            total_itinerary_distance_km=total_itinerary_distance,
        )

    def _to_response(self, spot: TravelSpot) -> TravelSpotResponse:
        return TravelSpotResponse(
            id=spot.id,
            name=spot.name,
            region=spot.region,
            address=spot.address,
            category=spot.category,
            latitude=spot.latitude,
            longitude=spot.longitude,
            description=spot.description,
            metadata=spot.spot_metadata,
            created_at=spot.created_at,
            updated_at=spot.updated_at,
        )


travel_service = TravelService()
