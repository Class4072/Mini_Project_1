import pytest
from app.core.code_mapper import code_mapper
from app.core.route_planner import route_planner
from app.schemas.ai import AIScheduleRequest


class TestCodeMapperAndRoutePlanner:
    """코드 매핑 및 카테고리 슬롯팅 동선 최적화 테스트"""

    def test_code_mapper_resolution(self):
        """02_요청 데이터 명세 초안 코드값 해석 검증"""
        # 1. 지역 코드 변환
        assert code_mapper.resolve_region_name("6") == "부산"
        assert code_mapper.resolve_region_name("1") == "서울"
        assert code_mapper.resolve_region_name("39") == "제주"
        assert code_mapper.resolve_region_name("BUSAN") == "부산"

        # 2. 동행 코드 해석
        name, tags = code_mapper.get_companion_info("FRIENDS", 3)
        assert name == "친구"
        assert "친구" in tags

        # 3. 테마 코드 해석
        theme_str = code_mapper.get_theme_descriptions(["FOOD", "NATURE"])
        assert "미식·맛집" in theme_str
        assert "자연·풍경" in theme_str

        # 4. 일정 밀도 및 시작 시간
        assert code_mapper.get_spots_per_day("NORMAL") == 4
        assert code_mapper.get_spots_per_day("RELAXED") == 3
        assert code_mapper.get_spots_per_day("PACKED") == 5
        assert code_mapper.get_start_time_hour("NORMAL") == 10
        assert code_mapper.get_start_time_hour("EARLY") == 8
        assert code_mapper.get_start_time_hour("LATE") == 11

    def test_haversine_distance_calculation(self):
        """Haversine 공식 거리 계산 정확도 검증 (해운대 ~ 광안리)"""
        # 해운대 (35.1587, 129.1603) <-> 광안리 (35.1530, 129.1180) 직선거리 약 3.8 ~ 4.0km
        dist = route_planner.calculate_distance_km(35.1587, 129.1603, 35.1530, 129.1180)
        assert 3.5 <= dist <= 4.5

    def test_category_aware_itinerary_slots(self):
        """카테고리 연속 방지 및 [식사 ➡️ 카페 or 컨텐츠] 순서 및 동선 가중치 검증"""
        spots = [
            # 식당 근처(0.8km)의 카페
            {"id": "c_near", "name": "식당 바로 옆 카페", "category": "카페/커피", "latitude": 35.162, "longitude": 129.177, "score": 0.85},
            # 식당에서 먼(5km) 카페
            {"id": "c_far", "name": "멀리 떨어진 카페", "category": "카페/디저트", "latitude": 35.110, "longitude": 129.110, "score": 0.95},
            # 식당
            {"id": "r1", "name": "해운대 기와집 대구탕", "category": "맛집/한식", "latitude": 35.161, "longitude": 129.175, "score": 0.90},
            # 오전/오후 명소
            {"id": "a1", "name": "해운대 해변", "category": "자연/산책", "latitude": 35.158, "longitude": 129.160, "score": 0.88},
            {"id": "a2", "name": "부산 시립미술관", "category": "문화/전시", "latitude": 35.166, "longitude": 129.136, "score": 0.86},
        ]

        itinerary = route_planner.optimize_category_aware_itinerary(
            spots=spots,
            travel_days=1,
            spots_per_day=4,
        )

        assert len(itinerary) == 1
        day1 = itinerary[0]
        assert len(day1) == 4

        # 슬롯 패턴: [오전 컨텐츠] -> [점심 식사] -> [식사 후 인근 카페] -> [오후 컨텐츠]
        categories = [s["category"] for s in day1]
        assert "자연" in categories[0] or "문화" in categories[0]
        assert "맛집" in categories[1]
        assert "카페" in categories[2]
        assert "자연" in categories[3] or "문화" in categories[3]

        # 동선 가중치 검증: 점심 식사 후 점수 자체는 'c_far'가 더 높더라도,
        # 식당과의 거리 가중치(Distance Weighting) 덕분에 식당 바로 옆 'c_near'가 우선 선택되어야 함!
        post_meal_place = day1[2]
        assert post_meal_place["id"] == "c_near"


