import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.database import AsyncSessionLocal, init_db
from app.services.travel_service import travel_service
from app.schemas.travel import BulkTravelSpotCreate, TravelSpotCreate

SAMPLE_SPOTS = [
    # --- 강원도 강릉시 ---
    {
        "name": "안목해변 커피거리",
        "region": "강원도 강릉시",
        "address": "강원특별자치도 강릉시 창해로 14",
        "category": "카페",
        "latitude": 37.7718,
        "longitude": 128.9482,
        "description": "푸른 동해 바다를 바라보며 커피 한 잔의 여유를 즐길 수 있는 대한민국 대표 커피 명소입니다. 오션뷰 테라스 카페가 줄지어 있어 커플 및 혼자 여행객에게 최고입니다.",
        "metadata": {
            "companion_types": ["커플", "혼자", "친구"],
            "best_seasons": ["봄", "여름", "가을", "겨울"],
            "weather_suitability": ["맑음", "흐림", "비오는날_실내"],
            "tags": ["오션뷰", "감성카페", "디저트", "바다산책", "데이트코스"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    },
    {
        "name": "경포호수 및 가시연습지",
        "region": "강원도 강릉시",
        "address": "강원특별자치도 강릉시 저동",
        "category": "자연/산책",
        "latitude": 37.7963,
        "longitude": 128.9068,
        "description": "사계절 아름다운 호수 산책로와 자전거 라이딩 코스가 조성되어 있는 평화로운 힐링 스팟입니다. 봄에는 벚꽃, 가을에는 갈대가 절경을 이룹니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "혼자"],
            "best_seasons": ["봄", "가을"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["자전거", "호수산책", "벚꽃명소", "힐링", "자연"],
            "estimated_stay_min": 60,
            "cost_level": "무료"
        }
    },
    {
        "name": "하슬라아트월드",
        "region": "강원도 강릉시",
        "address": "강원특별자치도 강릉시 강동면 율곡로 1441",
        "category": "실내/문화",
        "latitude": 37.7082,
        "longitude": 129.0118,
        "description": "동해 바다를 배경으로 한 복합 예술 공간 및 조각공원입니다. 독창적인 현대미술 전시와 인생샷을 남길 수 있는 포토존이 가득하여 비 오는 날에도 방문하기 좋습니다.",
        "metadata": {
            "companion_types": ["커플", "친구", "가족"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["비오는날_실내", "맑음"],
            "tags": ["미술관", "포토존", "이색체험", "실내데이트", "바다전망"],
            "estimated_stay_min": 120,
            "cost_level": "보통"
        }
    },
    {
        "name": "강릉 초당순두부마을",
        "region": "강원도 강릉시",
        "address": "강원특별자치도 강릉시 초당동",
        "category": "맛집",
        "latitude": 37.7912,
        "longitude": 128.9154,
        "description": "깨끗한 동해 바닷물로 간수를 맞춘 부드럽고 고소한 전통 초당순두부와 순두부 젤라또를 맛볼 수 있는 필수 미식 코스입니다.",
        "metadata": {
            "companion_types": ["가족", "커플", "친구", "혼자"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "비오는날_실내", "흐림"],
            "tags": ["순두부", "짬뽕순두부", "젤라또", "향토음식", "미식투어"],
            "estimated_stay_min": 60,
            "cost_level": "보통"
        }
    },
    {
        "name": "정동진 바다부채길",
        "region": "강원도 강릉시",
        "address": "강원특별자치도 강릉시 강동면 심곡리",
        "category": "자연/트레킹",
        "latitude": 37.6685,
        "longitude": 129.0435,
        "description": "2300만 년 전 지각변동을 관찰할 수 있는 해안단구 탐방로로 웅장한 기암괴석과 동해의 에메랄드빛 파도를 바로 옆에서 걷는 힐링 트레킹 코스입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "친구"],
            "best_seasons": ["봄", "가을", "여름"],
            "weather_suitability": ["맑음", "시원한"],
            "tags": ["해안트레킹", "파도소리", "바다풍경", "기암괴석", "인생샷"],
            "estimated_stay_min": 90,
            "cost_level": "저렴"
        }
    },

    # --- 제주특별자치도 ---
    {
        "name": "섭지코지 및 유민미술관",
        "region": "제주특별자치도 서귀포시",
        "address": "제주특별자치도 서귀포시 성산읍 고성리",
        "category": "자연/문화",
        "latitude": 33.4243,
        "longitude": 126.9311,
        "description": "아름다운 해안 절경과 안도 타다오가 설계한 건축미를 감상할 수 있는 명소입니다. 드넓은 바다와 성산일출봉을 한눈에 담을 수 있습니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "혼자"],
            "best_seasons": ["봄", "가을", "여름"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["해안절경", "안도타다오", "산책로", "성산일출봉전망", "힐링"],
            "estimated_stay_min": 100,
            "cost_level": "보통"
        }
    },
    {
        "name": "아르떼뮤지엄 제주",
        "region": "제주특별자치도 제주시",
        "address": "제주특별자치도 제주시 애월읍 어림비로 478",
        "category": "실내/문화",
        "latitude": 33.3982,
        "longitude": 126.3551,
        "description": "몰입형 미디어아트 전시관으로 빛과 소리가 빚어내는 화려한 예술을 감상할 수 있습니다. 비 오는 날이나 날씨와 무관하게 감동을 주는 최고의 실내 코스입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "친구", "아이동반"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["비오는날_실내", "맑음", "더운날"],
            "tags": ["미디어아트", "실내명소", "비오는날", "포토존", "감성체험"],
            "estimated_stay_min": 120,
            "cost_level": "보통"
        }
    },
    {
        "name": "협재해수욕장 및 금능해변",
        "region": "제주특별자치도 제주시",
        "address": "제주특별자치도 제주시 한림읍 한림로 329",
        "category": "자연/바다",
        "latitude": 33.3938,
        "longitude": 126.2396,
        "description": "에메랄드빛 투명한 바다와 비양도가 한눈에 펼쳐지는 제주의 대표 힐링 해변입니다. 얕은 수심과 고운 모래사장으로 가족 및 연인들의 산책과 일몰 감상에 완벽합니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "혼자", "친구"],
            "best_seasons": ["여름", "봄", "가을"],
            "weather_suitability": ["맑음", "따뜻한"],
            "tags": ["에메랄드바다", "일몰명소", "비양도", "해변산책", "물놀이"],
            "estimated_stay_min": 80,
            "cost_level": "무료"
        }
    },

    # --- 부산광역시 ---
    {
        "name": "해운대 블루라인파크 (해변열차/스카이캡슐)",
        "region": "부산광역시 해운대구",
        "address": "부산광역시 해운대구 달맞이길62번길 13",
        "category": "액티비티/체험",
        "latitude": 35.1587,
        "longitude": 129.1724,
        "description": "해운대 미포에서 송정까지 이어지는 아름다운 동해 남부 해안 절경을 레일 위에서 감상할 수 있는 관광 열차입니다. 연인과의 로맨틱한 드라이브 감성을 선사합니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "친구"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "선선한", "흐림"],
            "tags": ["해변열차", "스카이캡슐", "오션뷰", "데이트코스", "인기명소"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    },
    {
        "name": "SEA LIFE 부산아쿠아리움",
        "region": "부산광역시 해운대구",
        "address": "부산광역시 해운대구 해운대해변로 266",
        "category": "실내/문화",
        "latitude": 35.1593,
        "longitude": 129.1611,
        "description": "250여 종 1만여 마리의 해양 생물을 관람할 수 있는 초대형 실내 수족관입니다. 비 오는 날이나 쌀쌀한 날씨에 비를 맞지 않고 쾌적하게 관람할 수 있습니다.",
        "metadata": {
            "companion_types": ["가족", "아이동반", "커플", "친구"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["비오는날_실내", "맑음"],
            "is_indoor": True,
            "tags": ["아쿠아리움", "실내데이트", "가족여행", "비오는날", "해양생물"],
            "estimated_stay_min": 120,
            "cost_level": "보통"
        }
    },
    {
        "name": "해운대 기와집 대구탕",
        "region": "부산광역시 해운대구",
        "address": "부산광역시 해운대구 달맞이길104번길 46",
        "category": "맛집",
        "latitude": 35.1612,
        "longitude": 129.1752,
        "description": "시원하고 담백한 맑은 대구탕으로 유명한 부산의 대표 노포 미식 명소입니다. 비 오거나 쌀쌀한 날 따뜻한 국물 요리로 몸을 녹이기 좋습니다.",
        "metadata": {
            "companion_types": ["친구", "가족", "혼자", "커플"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["비오는날_실내", "맑음"],
            "is_indoor": True,
            "tags": ["대구탕", "국물요리", "해장", "노포맛집", "점심추천"],
            "estimated_stay_min": 60,
            "cost_level": "보통"
        }
    },
    {
        "name": "달맞이길 랑데자뷰 카페",
        "region": "부산광역시 해운대구",
        "address": "부산광역시 해운대구 달맞이길 117번가길 175",
        "category": "카페",
        "latitude": 35.1585,
        "longitude": 129.1820,
        "description": "통창 너머로 시원하게 펼쳐지는 해운대 바다를 바라보며 커피와 디저트를 즐길 수 있는 감성 오션뷰 카페입니다. 비 내리는 바다 풍경을 감상하기 제격입니다.",
        "metadata": {
            "companion_types": ["커플", "친구", "혼자"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["비오는날_실내", "맑음"],
            "is_indoor": True,
            "tags": ["오션뷰", "감성카페", "디저트", "통창뷰", "포토존"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    },
    {
        "name": "흰여울문화마을",
        "region": "부산광역시 영도구",
        "address": "부산광역시 영도구 영선동4가 1044-6",
        "category": "자연/산책",
        "latitude": 35.0786,
        "longitude": 129.0456,
        "description": "영도 절벽 위에 자리잡은 한국의 산토리니라 불리는 감성 마을입니다. 좁은 골목길 사이로 내려다보이는 바다와 이색 카페, 영화 변호인 촬영지로 유명합니다.",
        "metadata": {
            "companion_types": ["커플", "혼자", "친구"],
            "best_seasons": ["봄", "가을"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["골목투어", "감성마을", "포토존", "바다조망", "산책"],
            "estimated_stay_min": 100,
            "cost_level": "무료"
        }
    },
    {
        "name": "자갈치시장 신동아수산물센터",
        "region": "부산광역시 중구",
        "address": "부산광역시 중구 자갈치로 42",
        "category": "맛집",
        "latitude": 35.0970,
        "longitude": 129.0305,
        "description": "살아있는 활어회와 숯불 꼼장어구이를 맛볼 수 있는 대한민국 최대 수산시장입니다. 부산 특유의 활기와 정겨운 인심을 온몸으로 느낄 수 있는 필수 저녁 코스입니다.",
        "metadata": {
            "companion_types": ["친구", "가족", "커플"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "비오는날_실내"],
            "is_indoor": True,
            "tags": ["수산시장", "활어회", "꼼장어", "저녁식사", "해산물"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    },

    # --- 경상북도 경주시 ---
    {
        "name": "황리단길 감성 투어",
        "region": "경상북도 경주시",
        "address": "경상북도 경주시 포석로 1080",
        "category": "카페/문화",
        "latitude": 35.8364,
        "longitude": 129.2089,
        "description": "전통 한옥의 고즈넉함과 세련된 트렌드가 어우러진 경주의 핫플레이스입니다. 아기자기한 소품샵, 한옥 카페, 감성 맛집들이 밀집해 있습니다.",
        "metadata": {
            "companion_types": ["커플", "친구", "혼자"],
            "best_seasons": ["봄", "가을", "사계절"],
            "weather_suitability": ["맑음", "선선한", "흐림"],
            "tags": ["한옥카페", "소품샵", "길거리음식", "감성골목", "데이트"],
            "estimated_stay_min": 120,
            "cost_level": "보통"
        }
    },
    {
        "name": "동궁과 월지 (안압지 야경)",
        "region": "경상북도 경주시",
        "address": "경상북도 경주시 원화로 102",
        "category": "문화/역사",
        "latitude": 35.8341,
        "longitude": 129.2266,
        "description": "신라 왕궁의 별궁 터로, 밤이 되면 호수 위에 반사되는 누각과 조명이 환상적인 야경을 연출하는 대한민국 최고의 야경 힐링 명소입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "친구", "혼자"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "선선한", "야간"],
            "tags": ["야경명소", "신라역사", "호수야경", "산책로", "인생샷"],
            "estimated_stay_min": 60,
            "cost_level": "저렴"
        }
    }
]


async def seed_data():
    print("Initializing Database schema for TravelSpots...")
    await init_db()

    async with AsyncSessionLocal() as db:
        print(f"Seeding {len(SAMPLE_SPOTS)} travel spots across Korea...")
        bulk_obj = BulkTravelSpotCreate(
            spots=[TravelSpotCreate(**s) for s in SAMPLE_SPOTS]
        )
        created_spots = await travel_service.create_bulk_spots(db, bulk_obj)
        print(f"Successfully inserted {len(created_spots)} travel spots with 768-dim embeddings!")


if __name__ == "__main__":
    asyncio.run(seed_data())
