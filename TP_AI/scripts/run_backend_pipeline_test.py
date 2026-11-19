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

# 경기도 가평군 대표 휴양/힐링 여행 스팟
GAPYEONG_SPOTS = [
    {
        "name": "아침고요수목원",
        "region": "경기도 가평군",
        "address": "경기도 가평군 상면 수목원로 432",
        "category": "자연/힐링",
        "latitude": 37.7437,
        "longitude": 127.3524,
        "description": "축령산 자락에 조성된 한국을 대표하는 정원형 수목원. 울창한 잣나무 숲과 사계절 야생화 정원, 피톤치드 산책길이 있어 도심을 벗어나 편안하게 휴양하기에 완벽한 명소입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "부모님동반"],
            "best_seasons": ["봄", "가을", "사계절"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["수목원", "피톤치드", "잣나무숲", "산책로", "힐링명소", "포토존"],
            "estimated_stay_min": 120,
            "cost_level": "보통"
        }
    },
    {
        "name": "자라섬 남도 꽃정원 & 수변산책로",
        "region": "경기도 가평군",
        "address": "경기도 가평군 가평읍 자라섬로 60",
        "category": "자연/산책",
        "latitude": 37.8188,
        "longitude": 127.5255,
        "description": "북한강 물줄기로 둘러싸인 생태 테마 섬으로, 가을철 드넓은 꽃밭(구절초, 백일홍)과 버드나무 군락지가 펼쳐져 평화롭게 산책하며 물멍과 휴식을 즐기기 좋은 자연 휴양지입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "혼자"],
            "best_seasons": ["가을", "봄"],
            "weather_suitability": ["맑음", "선선한"],
            "tags": ["자라섬", "꽃밭", "북한강산책", "물멍", "피크닉", "평화로운"],
            "estimated_stay_min": 90,
            "cost_level": "무료"
        }
    },
    {
        "name": "청평호반 북한강 드라이브 & 감성 리버뷰 카페",
        "region": "경기도 가평군",
        "address": "경기도 가평군 설악면 자잠로 70",
        "category": "카페/디저트",
        "latitude": 37.6974,
        "longitude": 127.5082,
        "description": "북한강과 청평호의 잔잔한 물결을 마주보며 테라스에서 여유롭게 커피와 갓 구운 베이커리를 즐길 수 있는 힐링 리버뷰 카페. 북한강변 드라이브 코스의 핵심 쉼터입니다.",
        "metadata": {
            "companion_types": ["커플", "친구"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "비오는날_실내", "흐림"],
            "tags": ["리버뷰카페", "북한강드라이브", "물멍", "테라스카페", "휴양힐링"],
            "estimated_stay_min": 80,
            "cost_level": "보통"
        }
    },
    {
        "name": "가평 원조 잣두부정식 & 한방보쌈 건강밥상",
        "region": "경기도 가평군",
        "address": "경기도 가평군 상면 수목원로 248",
        "category": "맛집/향토음식",
        "latitude": 37.7512,
        "longitude": 127.3789,
        "description": "가평 특산물인 고소한 잣을 넣어 정성껏 빚은 담백한 잣두부 전골과 부드러운 한방 보쌈을 맛볼 수 있는 정갈한 힐링 건강 미식 식당입니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "부모님동반"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "비오는날_실내", "흐림"],
            "tags": ["가평잣두부", "향토음식", "건강식", "미식투어", "웰빙식사"],
            "estimated_stay_min": 60,
            "cost_level": "보통"
        }
    },
    {
        "name": "쁘띠프랑스 & 이탈리아마을",
        "region": "경기도 가평군",
        "address": "경기도 가평군 청평면 호반로 1063",
        "category": "문화/이색체험",
        "latitude": 37.7145,
        "longitude": 127.4907,
        "description": "청평호수를 내려다보는 언덕에 자리잡은 이국적인 유럽풍 문화 마을. 파스텔톤 지중해 건물과 호반 드라이브 코스가 어우러져 한적하게 힐링하기 좋습니다.",
        "metadata": {
            "companion_types": ["커플", "가족", "친구"],
            "best_seasons": ["사계절"],
            "weather_suitability": ["맑음", "흐림"],
            "tags": ["유럽감성", "이국적", "호반전망", "드라이브코스", "인생샷"],
            "estimated_stay_min": 90,
            "cost_level": "보통"
        }
    }
]

async def ensure_gapyeong_spots(db):
    stmt = select(TravelSpot).where(TravelSpot.region.ilike("%가평%"))
    res = await db.execute(stmt)
    existing = res.scalars().all()
    if not existing:
        print(f"[데이터 적재] 가평군 스팟 {len(GAPYEONG_SPOTS)}건 벡터 임베딩 생성 및 DB 저장 중...")
        bulk_obj = BulkTravelSpotCreate(
            spots=[TravelSpotCreate(**s) for s in GAPYEONG_SPOTS]
        )
        created = await travel_service.create_bulk_spots(db, bulk_obj)
        print(f"가평군 스팟 {len(created)}건 등록 완료!")
    else:
        print(f"가평군 스팟 {len(existing)}건이 이미 DB에 존재합니다.")

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. 예시값 수신 (Backend Request DTO)
    # -------------------------------------------------------------
    backend_input = {
        "region": "경기도 가평",
        "start_date": "2026-09-30",
        "end_date": "2026-10-01",
        "person_count": 2,
        "companion_type": "커플",
        "theme": "휴양여행",
        "transportation": "자동차"
    }
    print("=" * 60)
    print("1. [BACKEND] 예시 입력값 수신 완료")
    print("=" * 60)
    print(json.dumps(backend_input, indent=2, ensure_ascii=False))

    # -------------------------------------------------------------
    # 2. 벡터 DB 조회
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("2. [VECTOR DB] pgvector 시맨틱 검색 수행 중...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        await ensure_gapyeong_spots(db)
        
        search_query = f"{backend_input['region']} 1박 2일 {backend_input['theme']} 자연 숲 호수 힐링 드라이브 맛집 카페"
        search_results = await travel_service.search_spots(
            db=db,
            query=search_query,
            region="가평",
            top_k=5
        )

    retrieved_spots = []
    for item in search_results:
        spot = item["spot"]
        retrieved_spots.append({
            "spot_id": str(spot.id),
            "rank": item["rank"],
            "name": spot.name,
            "region": spot.region,
            "category": spot.category,
            "address": spot.address,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "similarity_score": item["similarity_score"],
            "description": spot.description,
            "tags": spot.metadata.get("tags", []) if spot.metadata else [],
            "stay_duration_min": spot.metadata.get("estimated_stay_min", 90) if spot.metadata else 90
        })

    print(f"벡터 DB 조회 완료 (총 {len(retrieved_spots)}개 스팟 검색됨)")
    for s in retrieved_spots:
        print(f" - {s['rank']}위: {s['name']} [{s['category']}] (유사도: {s['similarity_score']})")

    # -------------------------------------------------------------
    # 3. LLM 전달용 페이로드 구성 및 Ollama (travel-llama3) 호출
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"3. [LLM] JSON 가공 및 {MODEL_NAME} 호출")
    print("=" * 60)

    user_prompt = f"""[사용자 여행 요청 조건]
- 지역: {backend_input['region']}
- 기간: {backend_input['start_date']} ~ {backend_input['end_date']} (1박 2일)
- 인원: {backend_input['person_count']}인 ({backend_input['companion_type']})
- 테마: {backend_input['theme']} (힐링, 자연, 여유로운 쉼)
- 이동수단: {backend_input['transportation']} (자동차 드라이브)

[벡터 DB 시맨틱 검색 결과 (Top {len(retrieved_spots)})]
{json.dumps(retrieved_spots, indent=2, ensure_ascii=False)}

[작성 요구사항]
1. 1박 2일(Day 1: 9/30, Day 2: 10/1) 일정으로 오전/점심/오후 추천 동선을 구성하세요.
2. 각 스팟별:
   - 추천 시간대 및 체류시간
   - 휴양여행 관점에서의 선정 이유
   - 2인 커플 맞춤형 힐링 팁
3. 전체 자동차 드라이브 동선 요약과 총평을 남겨주세요.
"""

    llm_request_payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.6,
            "top_p": 0.9
        }
    }

    # LLM 전달 JSON 저장
    llm_req_file = os.path.join(OUTPUT_DIR, "backend_pipeline_request.json")
    with open(llm_req_file, "w", encoding="utf-8") as f:
        json.dump(llm_request_payload, f, indent=2, ensure_ascii=False)
    print(f"LLM 전달 JSON 파일 저장 완료: {llm_req_file}")

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
            llm_res_json = json.loads(res_body)
            llm_content = llm_res_json.get("message", {}).get("content", "")
            print(f"LLM 응답 수신 완료! (소요 시간: {elapsed:.2f}초, 생성 토큰: {llm_res_json.get('eval_count')} tokens)")
    except Exception as e:
        print(f"LLM 호출 에러: {e}")
        return

    # -------------------------------------------------------------
    # 4. BACKEND 반환용 완성형 JSON 데이터 DTO 가공
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("4. [BACKEND RETURN] 백엔드 응답용 완성형 JSON DTO 가공")
    print("=" * 60)

    backend_response = {
        "status": "SUCCESS",
        "code": 200,
        "message": "맞춤형 AI 여행 일정이 성공적으로 생성되었습니다.",
        "data": {
            "request_info": backend_input,
            "vector_search_summary": {
                "total_retrieved": len(retrieved_spots),
                "retrieved_spots": retrieved_spots
            },
            "ai_itinerary": {
                "model_used": MODEL_NAME,
                "generation_time_sec": round(elapsed, 2),
                "generated_text": llm_content
            }
        },
        "timestamp": datetime.now().isoformat()
    }

    # 백엔드 반환 JSON 저장
    backend_res_file = os.path.join(OUTPUT_DIR, "backend_pipeline_response.json")
    with open(backend_res_file, "w", encoding="utf-8") as f:
        json.dump(backend_response, f, indent=2, ensure_ascii=False)
    print(f"백엔드 반환 완성형 JSON 파일 저장 완료: {backend_res_file}")

    print("\n" + "=" * 60)
    print("[최종 AI 생성 일정 미리보기]")
    print("=" * 60)
    print(llm_content)

if __name__ == "__main__":
    asyncio.run(main())

