import sys
import os
import json
import time
import urllib.request
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal
from app.services.travel_service import travel_service
from app.schemas.travel import BulkTravelSpotCreate, TravelSpotCreate
from app.models.travel import TravelSpot
from app.config import settings
from sqlalchemy import select

OLLAMA_URL = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
MODEL_NAME = settings.OLLAMA_MODEL
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

# 경기도 시흥시 대표 여행 스팟 (기념일 데이트 특화)
SIHEUNG_SPOTS = [
    {
        "name": "오이도 빨간등대 & 해양산책로",
        "region": "경기도 시흥시",
        "address": "경기도 시흥시 오이도로 175",
        "category": "자연/바다/명소",
        "latitude": 37.3452,
        "longitude": 126.6876,
        "description": "서해 바다의 아름다운 붉은 낙조와 랜드마크 빨간등대가 어우러진 대표 데이트 명소. 바다 위를 걷는 듯한 산책로와 생명나무 전망대, 싱싱한 해산물/조개구이 거리가 있어 기념일 저녁 코스로 최고입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "친구"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "선선한", "일몰"],
            "tags": ["일몰명소", "오이도빨간등대", "해변산책", "조개구이", "데이트코스"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    },
    {
        "name": "배곧 한울공원 & 해수풀장 수변산책로",
        "region": "경기도 시흥시",
        "address": "경기도 시흥시 해송십리로 61",
        "category": "자연/공원",
        "latitude": 37.3621,
        "longitude": 126.7118,
        "description": "이국적인 야자수 파라솔과 바다 건너 송도 신도시 뷰를 감상할 수 있는 감성 수변 공원. 해질녘 노을이 환상적이며 연인들의 로맨틱한 드라이브 및 산책 코스로 유명합니다.",
        "metadata": {
            "companion_types": ["커플", "가족"],
            "best_seasons": ["봄", "여름", "가을"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["수변공원", "노을맛집", "감성스팟", "산책로", "인생샷"],
            "estimated_stay_min": 80,
            "cost_level": "무료"
        }
    },
    {
        "name": "시흥 갯골생태공원 (흔들전망대)",
        "region": "경기도 시흥시",
        "address": "경기도 시흥시 동서로 287",
        "category": "자연/생태",
        "latitude": 37.3917,
        "longitude": 126.7825,
        "description": "국가습지보호구역으로 내만 갯골과 옛 소금창고 염전이 보존된 친환경 힐링 공원. 22m 높이의 목조 흔들전망대에서 드넓은 갈대밭과 갯골 전경을 360도로 조망할 수 있는 감성 포토존입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "혼자"],
            "best_seasons": ["봄", "가을"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["흔들전망대", "갈대밭", "염전체험", "피크닉", "인생샷"],
            "estimated_stay_min": 100,
            "cost_level": "저렴"
        }
    },
    {
        "name": "물왕호수(물왕저수지) 감성 카페 & 레이크뷰 다이닝",
        "region": "경기도 시흥시",
        "address": "경기도 시흥시 물왕동 산32-1",
        "category": "카페/맛집",
        "latitude": 37.3888,
        "longitude": 126.8322,
        "description": "잔잔한 호수를 내려다보며 여유를 즐길 수 있는 대형 감성 베이커리 카페와 고급 스테이크/파스타 레스토랑이 밀집한 시흥 대표 기념일 데이트 및 낭만 드라이브 코스입니다.",
        "metadata": {
            "companion_types": ["커플", "가족"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "비오는날_실내", "흐림"],
            "tags": ["호수뷰", "물왕저수지", "감성카페", "기념일레스토랑", "드라이브코스"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    },
    {
        "name": "시화나래 조력공원 & 달전망대",
        "region": "경기도 시흥시",
        "address": "경기도 안산시 단원구 대부황금로 1927",
        "category": "실내/전망대",
        "latitude": 37.3142,
        "longitude": 126.6025,
        "description": "시화방조제 드라이브 코스 중심에 위치한 75m 높이의 원형 타워 전망대. 360도 통유리창과 아찔한 유리바닥 스카이워크에서 서해 바다와 조력발전소 절경을 조망할 수 있는 필수 드라이브 코스입니다.",
        "metadata": {
            "companion_types": ["커플", "가족"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "비오는날_실내", "선선한"],
            "tags": ["달전망대", "스카이워크", "서해바다", "드라이브코스", "오션뷰"],
            "estimated_stay_min": 60,
            "cost_level": "무료"
        }
    },
    {
        "name": "웨이브파크 (거북섬 해양복합레저단지)",
        "region": "경기도 시흥시",
        "address": "경기도 시흥시 거북섬둘레길 42",
        "category": "액티비티/체험",
        "latitude": 37.3278,
        "longitude": 126.6715,
        "description": "아시아 최대 규모의 인공 서핑 테마파크와 거북섬 수변 마리나 단지. 이색적인 서핑 감상, 야경 라운지 펍, 이국적인 산책로가 조성되어 있어 기념일에 특별하고 트렌디한 경험을 선사합니다.",
        "metadata": {
            "companion_types": ["커플", "친구"],
            "best_seasons": ["봄", "여름", "가을"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["거북섬", "인공서핑", "이색체험", "기념일데이트", "오션뷰펍"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    }
]

async def ensure_siheung_spots(db):
    stmt = select(TravelSpot).where(TravelSpot.region.ilike("%시흥%"))
    res = await db.execute(stmt)
    existing = res.scalars().all()
    if not existing:
        print(f"시흥시 여행 스팟이 DB에 없어 {len(SIHEUNG_SPOTS)}건을 벡터 임베딩 후 등록합니다...")
        bulk_obj = BulkTravelSpotCreate(
            spots=[TravelSpotCreate(**s) for s in SIHEUNG_SPOTS]
        )
        created = await travel_service.create_bulk_spots(db, bulk_obj)
        print(f"성공적으로 시흥시 스팟 {len(created)}건 등록 완료!")
    else:
        print(f"이미 DB에 시흥시 스팟 {len(existing)}건이 존재합니다.")

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("1. 시흥시 데이터 확인 및 벡터 DB 시맨틱 검색")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        await ensure_siheung_spots(db)
        
        query = "경기도 시흥 2박 3일 기념일 데이트 차로 이동하는 로맨틱 드라이브 코스 호수뷰 카페 맛집 일몰 명소"
        search_results = await travel_service.search_spots(
            db=db,
            query=query,
            region="시흥",
            top_k=6
        )

    retrieved_spots = []
    for item in search_results:
        spot = item["spot"]
        retrieved_spots.append({
            "순위": item["rank"],
            "장소명": spot.name,
            "지역": spot.region,
            "주소": spot.address,
            "카테고리": spot.category,
            "위도": spot.latitude,
            "경도": spot.longitude,
            "유사도점수": item["similarity_score"],
            "설명": spot.description,
            "태그": spot.metadata.get("tags", []) if spot.metadata else [],
            "추천동행": spot.metadata.get("companion_types", []) if spot.metadata else [],
            "체류시간(분)": spot.metadata.get("estimated_stay_min", 60) if spot.metadata else 60,
        })

    print(f"\n[벡터 DB 조회 결과 Top {len(retrieved_spots)}]")
    for s in retrieved_spots:
        print(f"- {s['순위']}위: {s['장소명']} ({s['카테고리']}, 유사도: {s['유사도점수']})")

    # LLM 페이로드 준비
    system_prompt = (
        "당신은 대한민국 최고 수준의 로맨틱 여행 전문 플래너 AI입니다. "
        "사용자가 전달한 [사용자 여행 조건]과 [벡터 DB 검색 결과]를 바탕으로 "
        "기념일에 어울리는 완벽한 2박 3일 맞춤형 자동차 드라이브 여행 일정을 작성해주세요. "
        "모든 설명, 팁, 일정은 100% 매끄럽고 감성적인 한국어로 작성해야 합니다."
    )

    user_prompt = f"""[사용자 여행 요청 조건]
- 지역: 경기도 시흥
- 여행 기간: 2026.09.30 ~ 2026.10.02 (2박 3일)
- 인원: 2인 (연인 커플)
- 여행 테마: 기념일 데이트 (로맨틱, 감성, 특별한 추억)
- 이동 수단: 자차 (드라이브 코스 고려)

[벡터 DB 시맨틱 검색 결과 (Top {len(retrieved_spots)})]
{json.dumps(retrieved_spots, indent=2, ensure_ascii=False)}

[작성 지침 및 요구사항]
1. 2박 3일(Day 1: 9/30, Day 2: 10/1, Day 3: 10/2) 일정으로 나누어 시간대별(오전, 점심, 오후, 일몰/저녁) 코스를 구성하세요.
2. 차량 이동에 따른 최적 드라이브 동선을 고려해 장소를 배치하세요.
3. 각 장소마다:
   - 추천 방문 시간대 및 체류 시간
   - 장소 선정 이유 (기념일 데이트 관점)
   - 커플 기념일 특별 팁 (포토존, 일몰 감상 포인트, 추천 메뉴 등)
4. 마지막에 '전체 동선 요약 및 기념일 데이트 총평'을 낭만적인 톤으로 작성하세요.
5. 반드시 모든 문장을 한국어로 작성하세요.
"""

    llm_request_payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        }
    }

    # 1. LLM으로 전달한 JSON 저장
    request_filepath = os.path.join(OUTPUT_DIR, "llm_request.json")
    with open(request_filepath, "w", encoding="utf-8") as f:
        json.dump(llm_request_payload, f, indent=2, ensure_ascii=False)
    print(f"\n[저장 완료] LLM 전달 JSON: {request_filepath}")

    print("\n" + "=" * 60)
    print(f"2. Ollama LLM ({MODEL_NAME} @ {OLLAMA_URL}) 호출 중...")
    print("=" * 60)

    req_data = json.dumps(llm_request_payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            res_body = response.read().decode("utf-8")
            elapsed = time.time() - start_time
            res_json = json.loads(res_body)

            # 2. LLM으로부터 받은 JSON 저장
            response_filepath = os.path.join(OUTPUT_DIR, "llm_response.json")
            with open(response_filepath, "w", encoding="utf-8") as f:
                json.dump(res_json, f, indent=2, ensure_ascii=False)
            print(f"[저장 완료] LLM 수신 JSON: {response_filepath}")

            print(f"\n[추론 완료] 소요 시간: {elapsed:.2f}초")
            content = res_json.get("message", {}).get("content", "")
            print("\n" + "=" * 60)
            print("3. Ollama 모델 응답 내용")
            print("=" * 60)
            print(content)

    except Exception as e:
        print(f"Ollama 호출 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())

