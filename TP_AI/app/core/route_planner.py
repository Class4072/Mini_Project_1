import math
from typing import List, Dict, Any, Optional, Union
from app.schemas.ai import MapViewport, MapBounds


class RoutePlanner:
    """위경도 좌표를 활용한 거리 계산, 최적 동선 정렬 및 일자별 일정 분할 엔진"""

    EARTH_RADIUS_KM = 6371.0  # 지구 반경 (km)
    AVERAGE_SPEED_KMH = 35.0  # 여행지 간 기본 평균 이동 속도 (시속 35km 기준)

    @classmethod
    def calculate_distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine 공식 기반 두 지점 간의 직선 거리(km) 계산 (부동소수점 도메인 에러 방어)"""
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        # 부동소수점 정밀도 오차로 인한 math domain error 방어
        a = min(1.0, max(0.0, a))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return round(cls.EARTH_RADIUS_KM * c, 2)

    @classmethod
    def estimate_travel_time_min(cls, distance_km: float, transport: Optional[str] = None) -> int:
        """이동 수단(CAR/PUBLIC_TRANSIT/WALK) 및 거리에 따른 정밀 예상 소요 시간(분) 계산"""
        if distance_km <= 0.1:
            return 0

        transport_clean = (transport or "CAR").upper()
        if "WALK" in transport_clean or "도보" in transport_clean:
            # 도보: 평균 4.5km/h, 도로 굴곡률 1.15
            hours = (distance_km * 1.15) / 4.5
            return max(3, int(math.ceil(hours * 60)))
        elif "TRANSIT" in transport_clean or "대중교통" in transport_clean:
            # 대중교통: 평균 22km/h + 대기/환승 버퍼 8분
            hours = (distance_km * 1.25) / 22.0
            return max(8, int(math.ceil(hours * 60)) + 8)
        else:
            # 자가용/렌터카 (CAR): 평균 38km/h, 도로 굴곡률 1.25 + 주차 버퍼 5분
            hours = (distance_km * 1.25) / 38.0
            return max(5, int(math.ceil(hours * 60)) + 5)

    @classmethod
    def calculate_map_viewport(cls, spots: List[Any]) -> Optional[MapViewport]:
        """장소 목록의 위경도로부터 카카오맵 중심 좌표 및 뷰포트 Bounds 계산"""
        valid_coords = []
        for s in spots:
            lat = s.get("latitude") if isinstance(s, dict) else getattr(s, "latitude", None)
            lon = s.get("longitude") if isinstance(s, dict) else getattr(s, "longitude", None)
            if lat is not None and lon is not None:
                valid_coords.append((float(lat), float(lon)))

        if not valid_coords:
            return None

        lats = [c[0] for c in valid_coords]
        lons = [c[1] for c in valid_coords]

        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        center_lat = round(sum(lats) / len(lats), 6)
        center_lon = round(sum(lons) / len(lons), 6)

        return MapViewport(
            centerLatitude=center_lat,
            centerLongitude=center_lon,
            bounds=MapBounds(
                minLatitude=round(min_lat, 6),
                maxLatitude=round(max_lat, 6),
                minLongitude=round(min_lon, 6),
                maxLongitude=round(max_lon, 6),
            ),
        )

    @classmethod
    def optimize_spot_order(cls, spots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Greedy Nearest Neighbor 기법을 적용하여 이동 거리를 최소화하는 순서로 스팟 정렬"""
        if len(spots) <= 2:
            return spots

        unvisited = spots.copy()
        # 첫 번째 스팟을 시작점으로 선정
        current = unvisited.pop(0)
        ordered = [current]

        while unvisited:
            next_spot = min(
                unvisited,
                key=lambda s: cls.calculate_distance_km(
                    current["latitude"], current["longitude"],
                    s["latitude"], s["longitude"]
                ),
            )
            unvisited.remove(next_spot)
            ordered.append(next_spot)
            current = next_spot

        return ordered

    @classmethod
    def optimize_category_aware_itinerary(
        cls,
        spots: List[Dict[str, Any]],
        travel_days: int = 1,
        spots_per_day: int = 4,
    ) -> List[List[Dict[str, Any]]]:
        """식사 시간대 식당 배치 및 [식사 ➡️ 카페 or 컨텐츠] 자연스러운 시퀀스 & 동선 가중치 최적화"""
        if not spots:
            return []

        # 1. 카테고리별 분류 풀 생성
        def is_restaurant(s):
            cat = s.get("category", "")
            return any(k in cat for k in ["맛집", "식당", "음식", "미식", "푸드", "요리", "수산물", "대구탕", "순두부", "고기", "밥"])

        def is_cafe(s):
            cat = s.get("category", "")
            return any(k in cat for k in ["카페", "디저트", "베이커리", "커피", "찻집", "티타임"])

        restaurants = [s for s in spots if is_restaurant(s)]
        cafes = [s for s in spots if is_cafe(s)]
        contents = [s for s in spots if not is_restaurant(s) and not is_cafe(s)]

        all_pool = spots.copy()
        used_ids = set()

        daily_grouped = []

        # 하루 방문 수에 따른 자연스러운 여행자 행동 패턴 시퀀스
        # [식사] 직후에는 반드시 [카페] 또는 [컨텐츠(가벼운 산책/전시)]가 순서대로 위치하도록 설계
        base_patterns = {
            3: ["content", "restaurant", "cafe"],  # 오전 명소 -> 점심 식사 -> 식사 후 카페
            4: ["content", "restaurant", "cafe", "content"],  # 오전 명소 -> 점심 식사 -> 식사 후 카페 -> 오후 컨텐츠
            5: ["content", "restaurant", "cafe", "content", "restaurant"],  # ... -> 저녁 식사
            6: ["content", "restaurant", "cafe", "content", "restaurant", "content"], # ... -> 저녁 후 야경/컨텐츠
        }

        pattern = base_patterns.get(
            spots_per_day,
            ["content", "restaurant", "cafe", "content"]
        )
        if spots_per_day > len(pattern):
            # 6곳 초과 시 [카페/컨텐츠]를 번갈아 추가
            extra = ["cafe", "content"] * ((spots_per_day - len(pattern) + 1) // 2)
            pattern.extend(extra[: spots_per_day - len(pattern)])
        elif spots_per_day < len(pattern):
            pattern = pattern[:spots_per_day]

        daily_grouped = []
        prev_day_last_spot = None  # 이전 일차의 마지막 장소 (일자 간 이동 점프 방지 앵커)

        for day in range(1, travel_days + 1):
            day_schedule: List[Dict[str, Any]] = []
            # Day 2 이후 시작 시 직전 일차(Day 1)의 마지막 권역과 인접한 곳에서 하루를 시작하도록 연결
            current_loc = prev_day_last_spot


            for step_idx, slot_type in enumerate(pattern, start=1):
                prev_slot = pattern[step_idx - 2] if step_idx > 1 else None
                is_post_meal = (prev_slot == "restaurant")  # 직전이 식사였는지 여부

                candidate_pool = []
                if slot_type == "restaurant":
                    candidate_pool = [s for s in restaurants if s["id"] not in used_ids]
                elif slot_type == "cafe":
                    candidate_pool = [s for s in cafes if s["id"] not in used_ids]
                else:
                    candidate_pool = [s for s in contents if s["id"] not in used_ids]

                # 해당 카테고리가 부족할 경우: 식사 직후면 [카페 or 컨텐츠] 중 남은 것 우선 선택
                if not candidate_pool and is_post_meal:
                    candidate_pool = [
                        s for s in all_pool
                        if s["id"] not in used_ids and not is_restaurant(s)
                    ]

                # 그래도 없으면 이전 카테고리와 연속 중복되지 않는 미방문 장소
                if not candidate_pool:
                    prev_cat = day_schedule[-1]["category"] if day_schedule else None
                    candidate_pool = [
                        s for s in all_pool
                        if s["id"] not in used_ids and s.get("category") != prev_cat
                    ]

                # 최종 잔여 풀
                if not candidate_pool:
                    candidate_pool = [s for s in all_pool if s["id"] not in used_ids]

                if not candidate_pool:
                    break

                # 거리 가중치(Distance Weighting) 계산:
                # 특히 식사 직후 방문하는 카페/컨텐츠는 이동 피로도를 줄이기 위해 식당 인접 거리 가중치 대폭 적용
                def calculate_choice_priority(spot):
                    if not current_loc:
                        return spot.get("score", 1.0)

                    dist_km = cls.calculate_distance_km(
                        current_loc["latitude"], current_loc["longitude"],
                        spot["latitude"], spot["longitude"]
                    )
                    
                    # 식사 직후 장소는 거리 페널티를 더 강하게 적용 (인접한 곳 선호)
                    dist_decay = 0.6 if is_post_meal else 0.3
                    distance_factor = 1.0 / (1.0 + (dist_km * dist_decay))
                    
                    base_score = spot.get("score", 1.0)
                    return base_score * distance_factor

                best_spot = max(candidate_pool, key=calculate_choice_priority)

                day_schedule.append(best_spot)
                used_ids.add(best_spot["id"])
                current_loc = best_spot

            if day_schedule:
                daily_grouped.append(day_schedule)
                prev_day_last_spot = day_schedule[-1]


        return daily_grouped



    @classmethod
    def build_itinerary(
        cls,
        spots: List[Dict[str, Any]],
        travel_days: int = 1,
        spots_per_day: int = 3,
    ) -> List[Dict[str, Any]]:
        """선정된 스팟들을 일자별(Day 1, Day 2...)로 나누고 이동 경로 및 소요 시간을 계산하여 일정 생성"""
        if not spots:
            return []

        # 1. 전체 이동 동선 최적화 정렬
        ordered_spots = cls.optimize_spot_order(spots)

        total_spots_needed = travel_days * spots_per_day
        selected_spots = ordered_spots[:total_spots_needed]

        itinerary = []
        spot_idx = 0

        for day in range(1, travel_days + 1):
            day_spots = selected_spots[spot_idx : spot_idx + spots_per_day]
            spot_idx += spots_per_day

            if not day_spots:
                break

            day_routes = []
            prev_spot = None

            for order_idx, spot in enumerate(day_spots, start=1):
                dist_km = 0.0
                travel_min = 0
                
                if prev_spot is not None:
                    dist_km = cls.calculate_distance_km(
                        prev_spot["latitude"], prev_spot["longitude"],
                        spot["latitude"], spot["longitude"]
                    )
                    travel_min = cls.estimate_travel_time_min(dist_km)

                meta = spot.get("metadata", {})
                stay_min = meta.get("estimated_stay_min", 60)

                day_routes.append({
                    "order": order_idx,
                    "spot_id": spot["id"],
                    "name": spot["name"],
                    "category": spot["category"],
                    "address": spot.get("address"),
                    "latitude": spot["latitude"],
                    "longitude": spot["longitude"],
                    "description": spot["description"],
                    "stay_duration_min": stay_min,
                    "distance_from_prev_km": dist_km,
                    "estimated_travel_min": travel_min,
                    "tags": meta.get("tags", []),
                })
                prev_spot = spot

            total_day_distance = sum(r["distance_from_prev_km"] for r in day_routes)
            total_day_travel_time = sum(r["estimated_travel_min"] for r in day_routes)

            itinerary.append({
                "day": day,
                "title": f"Day {day} 코스 탐방",
                "total_spots": len(day_routes),
                "total_distance_km": round(total_day_distance, 2),
                "total_travel_time_min": total_day_travel_time,
                "routes": day_routes,
            })

        return itinerary


route_planner = RoutePlanner()
