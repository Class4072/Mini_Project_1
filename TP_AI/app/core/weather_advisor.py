from typing import Dict, Any, Optional
from datetime import datetime, date


class WeatherAdvisor:
    """여행 날짜, 계절 및 날씨 조건에 따른 여행 가이드 및 날씨 적합성 분석기"""

    SEASON_INFO = {
        "spring": {"months": [3, 4, 5], "name": "봄", "temp": "12°C ~ 20°C", "desc": "따뜻하고 꽃놀이 및 야외 산책에 이상적입니다."},
        "summer": {"months": [6, 7, 8], "name": "여름", "temp": "24°C ~ 32°C", "desc": "바다 물놀이, 계곡 및 시원한 실내 코스를 추천합니다."},
        "autumn": {"months": [9, 10, 11], "name": "가을", "temp": "14°C ~ 22°C", "desc": "청명한 하늘과 단풍, 드라이브 및 감성 여행에 최적입니다."},
        "winter": {"months": [12, 1, 2], "name": "겨울", "temp": "-3°C ~ 7°C", "desc": "눈 덮인 설경, 온천 및 따뜻한 카페/실내 문화 투어를 추천합니다."},
    }

    @classmethod
    def get_season(cls, target_date: Optional[date] = None) -> str:
        month = target_date.month if target_date else datetime.now().month
        for season_key, info in cls.SEASON_INFO.items():
            if month in info["months"]:
                return season_key
        return "spring"

    @classmethod
    def generate_weather_briefing(
        cls,
        region: str,
        target_date: Optional[date] = None,
        weather_preference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """선택한 지역과 날짜, 선호 날씨에 따른 날씨 브리핑 및 권장 복장/활동 팁 생성"""
        season_key = cls.get_season(target_date)
        season = cls.SEASON_INFO[season_key]

        date_str = target_date.strftime("%Y-%m-%d") if target_date else "예정일"
        pref = weather_preference or "맑음"

        # 날씨 선호도에 따른 안내 조정
        if "비" in pref or "실내" in pref:
            weather_status = "비 / 흐림 (실내 추천)"
            temperature = season["temp"]
            activity_tip = "비 오는 날 특유의 운치 있는 오션뷰 실내 카페, 미술관 및 실내 체험 코스가 최적입니다. 우산을 꼭 챙기세요."
        elif "눈" in pref:
            weather_status = "눈 / 맑음"
            temperature = "-4°C ~ 3°C"
            activity_tip = "겨울 설경과 따뜻한 힐링 스팟을 즐기기 좋습니다. 방한 외투와 미끄럼 방지 신발을 착용하세요."
        else:
            weather_status = f"맑고 쾌적함 ({season['name']} 시즌)"
            temperature = season["temp"]
            activity_tip = f"{season['desc']} 야외 활동과 사진 촬영에 매우 적합합니다."

        return {
            "target_date": date_str,
            "region": region,
            "season": season["name"],
            "expected_weather": weather_status,
            "expected_temperature": temperature,
            "travel_tip": activity_tip,
        }


weather_advisor = WeatherAdvisor()
