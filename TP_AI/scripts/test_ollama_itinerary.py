import sys
import os
import json
import time
import urllib.request
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal
from app.services.travel_service import travel_service
from app.config import settings

OLLAMA_URL = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
MODEL_NAME = settings.OLLAMA_MODEL

async def main():
    print("=" * 60)
    print("1. 벡터 DB 시맨틱 검색 수행 중...")
    print("=" * 60)
    
    query = "강릉 1박 2일 바다 전망 감성 카페와 맛집 미식 투어"
    region = "강릉"
    
    async with AsyncSessionLocal() as db:
        search_results = await travel_service.search_spots(
            db=db,
            query=query,
            region=region,
            top_k=5
        )
    
    # 벡터 DB 조회 결과 정리
    retrieved_spots = []
    for item in search_results:
        spot = item["spot"]
        retrieved_spots.append({
            "순위": item["rank"],
            "장소명": spot.name,
            "지역": spot.region,
            "카테고리": spot.category,
            "유사도점수": item["similarity_score"],
            "주소": spot.address,
            "설명": spot.description,
            "태그": spot.metadata.get("tags", []) if spot.metadata else [],
            "추천동행": spot.metadata.get("companion_types", []) if spot.metadata else [],
            "체류시간(분)": spot.metadata.get("estimated_stay_min", 60) if spot.metadata else 60,
        })
    
    print(f"\n[벡터 DB 조회 결과 (Top {len(retrieved_spots)})]")
    print(json.dumps(retrieved_spots, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print(f"2. Ollama LLM ({MODEL_NAME} @ {OLLAMA_URL}) 프롬프트 구성 및 호출")
    print("=" * 60)
    
    system_prompt = (
        "당신은 전문 여행 플래너 AI입니다. "
        "사용자가 제공한 [벡터 DB 검색 결과]를 바탕으로 논리적이고 알찬 여행 일정을 한국어로 작성해주세요. "
        "일정에 각 장소의 특징, 동선 고려 사항, 여행 꿀팁을 포함해야 합니다."
    )
    
    user_prompt = f"""[사용자 여행 요청]
- 여행지: 강원도 강릉
- 기간: 1박 2일
- 여행 테마: 바다 전망, 감성 카페, 지역 맛집 미식 투어
- 동행자: 연인(커플)

[벡터 DB 시맨틱 검색 결과 (Top {len(retrieved_spots)})]
{json.dumps(retrieved_spots, indent=2, ensure_ascii=False)}

[작성 요청사항]
위 벡터 DB 조회 결과를 기반으로 다음 항목을 작성해 주세요:
1. 1박 2일 일정 코스 (Day 1, Day 2로 나누어 방문 순서와 추천 시간대 제시)
2. 각 스팟별 추천 이유 및 커플 여행 팁
3. 이동 동선 및 일정 총평
"""

    payload = {
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
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    
    print("\nOllama 서버로 전송 중... (응답 대기)")
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_body = response.read().decode("utf-8")
            elapsed = time.time() - start_time
            res_json = json.loads(res_body)
            
            print(f"\n응답 완료! (소요 시간: {elapsed:.2f}초)")
            print("\n" + "=" * 60)
            print("3. Ollama 모델 응답 (여행 일정 결과)")
            print("=" * 60)
            content = res_json.get("message", {}).get("content", "")
            print(content)
            
            # 메타데이터 출력
            eval_count = res_json.get("eval_count")
            eval_duration = res_json.get("eval_duration", 0) / 1e9
            if eval_count and eval_duration:
                tok_per_sec = eval_count / eval_duration
                print(f"\n[성능 지표] 생성 토큰: {eval_count} tokens | 속도: {tok_per_sec:.2f} tokens/s")
                
    except Exception as e:
        print(f"Ollama 호출 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())

