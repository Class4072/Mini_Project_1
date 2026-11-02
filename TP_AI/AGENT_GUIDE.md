# 🤖 AI 에이전트(Antigravity) 협업 및 프로젝트 관리 가이드 (AGENT_GUIDE.md)

이 문서는 **AI 맞춤형 여행 추천 및 경로 안내 시스템 (TP_AI)** 프로젝트의 아키텍처 이해, 확장 개발, 그리고 AI 어시스턴트(Antigravity)를 효과적으로 다루기 위한 가이드입니다.

---

## 📌 1. 프로젝트 개요 및 핵심 아키텍처

사용자가 자연어 여행 조건(동행자, 테마, 기간, 날씨 선호 등)을 입력하면, **PostgreSQL `pgvector` 시맨틱 검색 + 조건 필터링 + 최적 경로 알고리즘**을 통해 **[추천 지역 + 일자별 일정 + 날씨 안내 + 최적 이동 경로]**를 완성형 데이터로 반환합니다.

### 📐 레이어별 구조
```text
TP_AI/
├── AGENT_GUIDE.md              # [본 문서] AI 협업 및 시스템 개발 가이드
├── README.md                   # 프로젝트 기본 설명서
├── .env                        # 로컬 환경 변수 & DB 비밀번호 (Git 제외)
├── requirements.txt            # 의존성 패키지 (FastAPI, pgvector, torch, sentence-transformers 등)
├── app/
│   ├── main.py                 # FastAPI 애플리케이션 진입점 & Lifespan 관리
│   ├── config.py               # Pydantic Settings 환경 설정
│   ├── database.py             # 비동기 SQLAlchemy 2.0 (asyncpg) & pgvector 확장 초기화
│   ├── core/
│   │   ├── embedding.py        # jhgan/ko-sroberta-multitask 768차원 임베딩 생성기 (싱글톤)
│   │   ├── route_planner.py    # Haversine & Nearest Neighbor 기반 최적 이동 경로 계산기
│   │   └── weather_advisor.py  # 여행 날짜/계절/날씨 적합성 분석 및 팁 생성기
│   ├── models/
│   │   └── travel.py           # TravelSpot 모델 (HNSW 코사인 인덱스 + GIN Trigram 인덱스)
│   ├── schemas/
│   │   └── travel.py           # Pydantic DTO (요청/응답 스키마)
│   ├── services/
│   │   └── travel_service.py   # 비즈니스 로직 및 전체 추천 파이프라인 오케스트레이션
│   └── api/
│       ├── deps.py             # DB 세션 의존성 주입
│       └── v1/
│           ├── router.py       # v1 라우터 통합
│           └── endpoints/
│               └── travel.py   # 여행 추천(/recommend), 검색(/search), 스팟 CRUD(/spots) API
└── scripts/
    ├── seed_travel_data.py     # 한국 주요 관광지 샘플 데이터 12건 일괄 삽입 스크립트
    └── test_travel_api.py      # 전체 API 엔드투엔드 통합 검증 스크립트
```

---

## 💬 2. AI 에이전트(Antigravity)를 다루는 효과적인 프롬프트 팁

AI에게 작업을 요청할 때 아래 형식으로 지시하시면 가장 정확하고 빠른 결과를 얻으실 수 있습니다:

### ① 기능 추가 요청 시
* **예시 프롬프트**:
  > "여행지 메타데이터에 `숙소_추천`(hotel) 항목을 추가하고, `/recommend` 응답에 하루 일정이 끝난 후 인근 숙소 1곳을 함께 묶어서 반환하도록 확장해줘."
  > "카카오 지도 API나 네이버 길찾기 URL 링크를 `routes` 응답의 각 스팟에 자동으로 생성해서 넣어줘."

### ② 외부 API 연동 요청 시
* **예시 프롬프트**:
  > "현재 `weather_advisor.py`의 룰베이스 날씨 대신 기상청 단기예보 Open API(또는 OpenWeatherMap)를 연동하는 클라이언트를 작성하고 비동기로 호출하도록 교체해줘."

### ③ SpringBoot 백엔드와의 연동 DTO 생성 요청 시
* **예시 프롬프트**:
  > "FastAPI의 `TravelRecommendResponse`와 1:1로 매핑되는 SpringBoot(Java)용 Record(또는 DTO) 클래스 코드를 작성해줘."

### ④ DB 스키마 수정 요청 시
* **예시 프롬프트**:
  > "TravelSpot 테이블에 `opening_hours`(영업시간)와 `closed_days`(휴무일) 컬럼을 추가하고, 사용자가 선택한 요일에 영업하지 않는 장소는 추천에서 제외하는 필터링을 추가해줘."

---

## 🔒 3. 보안 및 데이터베이스 원칙 (주의사항)

1. **민감 정보(비밀번호, API 키) 보호**:
   * DB URL, 비밀번호, 외부 API Key는 반드시 [`.env`](file:///D:/ToyProject/TP_AI/.env) 파일에만 작성합니다.
   * [`.gitignore`](file:///D:/ToyProject/TP_AI/.gitignore)에 `.env`가 등록되어 있으므로 Git에 커밋되지 않습니다.
2. **임베딩 차원 일치성**:
   * 모델: `jhgan/ko-sroberta-multitask` (차원: **768**)
   * DB 컬럼: `embedding = Column(Vector(768))`
   * *다른 모델로 변경 시 `.env`의 `EMBEDDING_DIMENSION`과 DB 테이블의 컬럼 크기를 일치시켜야 합니다.*
3. **인덱스 사양**:
   * 벡터 인덱스: HNSW (`m=16, ef_construction=64, vector_cosine_ops`)
   * 텍스트 인덱스: GIN (`gin_trgm_ops` for 한국어 부분 일치 및 오타 보정)

---

## 🛠️ 4. 서버 구동 및 테스트 명령어

### 가상환경 활성화 (PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
```

### 1. 여행지 기본 데이터 시딩
```powershell
python scripts/seed_travel_data.py
```

### 2. FastAPI 서버 실행
```powershell
uvicorn app.main:app --reload --port 8000
```
* **Swagger API 문서**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **상태 점검**: [http://localhost:8000/health](http://localhost:8000/health)

### 3. 전체 API 기능 통합 테스트
```powershell
python scripts/test_travel_api.py
```

---

## 🚀 5. 향후 확장 추천 로드맵 (Roadmap)

1. **실제 공공데이터/관광 API 연동**:
   * 한국관광공사 TourAPI 4.0을 연동하여 전국 수만 개 관광지/맛집/숙소 자동 수집 및 벡터화
2. **지도/길찾기 네비게이션 연동**:
   * 카카오 지도 / T-Map 경로 API를 연동하여 실제 도로 기준 실시간 자동차/대중교통 소요 시간 반영
3. **SpringBoot 또는 프론트엔드 연동**:
   * SpringBoot에서 WebClient로 본 FastAPI 추천 서버를 호출하여 앱/웹 서비스와 결합
