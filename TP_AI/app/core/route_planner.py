import math
from typing import List, Dict, Any, Optional


class RoutePlanner:
    """위경도 좌표를 활용한 거리 계산, 최적 동선 정렬 및 일자별 일정 분할 엔진"""

    EARTH_RADIUS_KM = 6371.0  # 지구 반경 (km)
    AVERAGE_SPEED_KMH = 35.0  # 여행지 간 평균 이동 속도 (시속 35km 기준)

    @classmethod
    def calculate_distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine 공식 기반 두 지점 간의 직선 거리(km) 계산"""
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(cls.EARTH_RADIUS_KM * c, 2)

    @classmethod
    def estimate_travel_time_min(cls, distance_km: float) -> int:
        """이동 거리에 따른 예상 소요 시간(분) 계산 (신호 대기 및 도로 굴곡 보정 x1.2)"""
        if distance_km <= 0.1:
            return 0
        actual_distance = distance_km * 1.25  # 도로 굴곡률 반영
        hours = actual_distance / cls.AVERAGE_SPEED_KMH
        minutes = int(math.ceil(hours * 60))
        return max(5, minutes)

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
