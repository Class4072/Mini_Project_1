# ✈️ AI 맞춤형 여행 추천 및 경로 안내 시스템 (TP_AI)

한국어 로컬 임베딩 모델(`jhgan/ko-sroberta-multitask`)과 **PostgreSQL `pgvector`**를 결합하여, 여행자가 원하는 조건(동행자, 테마, 기간, 날씨 등)에 맞춰 **[추천 지역 + 일자별 코스 + 날씨 브리핑 + 최적 이동 경로]**를 완성형 데이터로 제공하는 FastAPI AI 백엔드입니다.

---

## 🌟 주요 기능

1. **AI 여행 조건 시맨틱 분석 & 추천 (`POST /api/v1/travel/recommend`)**:
   * "커플이서 조용하게 바다 보며 힐링하고 감성 카페 가고 싶어" 같은 자연어 조건을 768차원 벡터로 변환
   * HNSW 코사인 유사도 검색과 메타데이터(동행자, 날씨, 카테고리) 가중치를 결합하여 최적의 여행지 도출
2. **날씨 & 계절 적합성 가이드**:
   * 여행 예정일자의 계절 및 날씨 선호도(맑음, 비오는날 실내, 눈 등)에 맞춘 여행 브리핑 및 복장/활동 팁 제공
3. **일자별 경로 최적화 (Route Optimization)**:
   * 선정된 스팟들의 위경도 좌표를 기반으로 이동 거리를 최소화하는 순서(Greedy Nearest Neighbor)로 정렬
   * Day 1, Day 2 일자별 스팟 순서, 스팟 간 이동 거리(km), 예상 이동 시간(분), 권장 체류 시간 산출
4. **여행 스팟 관리 및 시맨틱/키워드 검색**:
   * 여행지 단건/대량(Bulk) 등록 및 자동 벡터화
   * Trigram(GIN) + Vector(HNSW) 하이브리드 검색

---

## 📂 디렉터리 구조

```text
TP_AI/
├── README.md             # 프로젝트 개요 및 빠른 시작 가이드
├── .env                  # DB 접속 정보 및 환경 변수 (Git 추적 제외)
├── requirements.txt      # 의존성 패키지
├── app/
│   ├── main.py           # FastAPI 애플리케이션 진입점
│   ├── config.py         # 환경 변수 설정 (Pydantic Settings)
│   ├── database.py       # 비동기 DB 엔진 & 세션 관리 (SQLAlchemy 2.0 Async)
│   ├── core/
│   │   ├── embedding.py  # ko-sroberta 768차원 임베딩 생성기 (싱글톤)
│   │   ├── route_planner.py    # 위경도 거리 계산 및 경로 최적화 엔진
│   │   └── weather_advisor.py  # 날짜/계절/날씨 분석기
│   ├── models/
│   │   └── travel.py     # TravelSpot 모델 (HNSW 코사인 인덱스 + GIN Trigram 인덱스)
│   ├── schemas/
│   │   └── travel.py     # Pydantic DTO (추천 요청/응답, 스팟 CRUD)
│   ├── services/
│   │   └── travel_service.py # 추천 및 검색 비즈니스 로직
│   └── api/
│       ├── deps.py       # 의존성 주입
│       └── v1/
│           ├── router.py # API v1 라우터
│           └── endpoints/
│               └── travel.py # 추천/검색/스팟 API 엔드포인트
└── scripts/
    ├── seed_travel_data.py # 샘플 관광지 12개 데이터 시딩 스크립트
    └── test_travel_api.py  # 전체 API 통합 검증 스크립트
```

---

## 🚀 빠른 시작 가이드

### 1. 가상환경 활성화 & 의존성 확인

```powershell
# 가상환경 활성화 (PowerShell)
.\venv\Scripts\Activate.ps1

# 패키지 설치 (이미 완료된 경우 생략 가능)
pip install -r requirements.txt
```

### 2. 여행지 데이터 시딩 (최초 1회)

```powershell
python scripts/seed_travel_data.py
```
* 강릉, 제주, 부산, 경주 등 대표 관광지 12곳의 좌표, 설명, 메타데이터 및 768차원 임베딩이 DB에 저장됩니다.

### 3. FastAPI 서버 실행

```powershell
uvicorn app.main:app --reload --port 8000
```

* **Swagger 대화형 API 문서**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **서버 상태 확인**: [http://localhost:8000/health](http://localhost:8000/health)

### 4. 전체 기능 테스트

```powershell
python scripts/test_travel_api.py
```

---

## 📡 API 요청/응답 예시

### `POST /api/v1/travel/recommend` (AI 맞춤 여행 플랜 추천)

전달받는 핵심 입력 데이터는 **[지역, 시작 날짜, 종료 날짜, 인원 수]**입니다.

#### 요청 (Request)
```json
{
  "region": "강릉",
  "start_date": "2026-10-15",
  "end_date": "2026-10-16",
  "person_count": 2,
  "theme_or_keyword": "바다 전망과 감성 카페 투어 (선택 사항)"
}
```

#### 응답 (Response)
```json
{
  "request_summary": {
    "region": "강릉",
    "start_date": "2026-10-15",
    "end_date": "2026-10-16",
    "person_count": 2,
    "theme_or_keyword": "바다 전망과 감성 카페 투어 (선택 사항)",
    "spots_per_day": 3
  },
  "destination_summary": {
    "requested_region": "강릉",
    "theme": "바다 전망과 감성 카페 투어",
    "overview": "강릉 지역에서 커플 / 2인 친구 여행에 어울리는 대표 명소, 힐링 스팟 및 감성 카페를 연결한 맞춤형 코스입니다.",
    "companion_group": "커플 / 2인 친구 여행"
  },
  "weather_summary": {
    "target_date": "2026-10-15",
    "region": "강원도 강릉시",
    "season": "가을",
    "expected_weather": "맑고 쾌적함 (가을 시즌)",
    "expected_temperature": "14°C ~ 22°C",
    "travel_tip": "청명한 하늘과 단풍, 드라이브 및 감성 여행에 최적입니다. 야외 활동과 사진 촬영에 매우 적합합니다."
  },
  "itinerary": [
    {
      "day": 1,
      "date": "2026-10-15",
      "title": "Day 1 강원도 강릉시 핵심 명소 & 놀거리 코스",
      "total_spots": 2,
      "total_distance_km": 3.6,
      "total_travel_time_min": 8,
      "routes": [
        {
          "order": 1,
          "name": "안목해변 커피거리",
          "category": "카페",
          "stay_duration_min": 90,
          "distance_from_prev_km": 0.0,
          "estimated_travel_min": 0
        },
        {
          "order": 2,
          "name": "강릉 초당순두부마을",
          "category": "맛집",
          "stay_duration_min": 60,
          "distance_from_prev_km": 3.6,
          "estimated_travel_min": 8
        }
      ]
    }
  ],
  "total_days": 2,
  "total_spots_count": 4,
  "total_itinerary_distance_km": 17.06
```