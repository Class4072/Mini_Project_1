# ⚙️ Trp Batch Service Specification (BATCH.md)
> **Python 기반 공공데이터(TourAPI·기상청) 대용량 수집, 날씨·계절 태그 가공 및 pgvector 사전 임베딩 파이프라인**

```markdown
# 🔗 배치 서비스 Git 저장소 (Repository URL)
GIT_BATCH_REPO="https://github.com/<ORGANIZATION_OR_USER>/trp-batch"
```

---

## 📌 목차
1. [배치 서비스 개요](#1-배치-서비스-개요)
2. [배치 아키텍처 및 데이터 흐름](#2-배치-아키텍처-및-데이터-흐름)
3. [배치 작업(Job) 전체 명세 (BT-001 ~ BT-014)](#3-배치-작업job-전체-명세-bt-001--bt-014)
4. [RAG 벡터 임베딩 생성 파이프라인 (핵심)](#4-rag-벡터-임베딩-생성-파이프라인-핵심)
5. [기상청 날씨 데이터 수집 및 동기화 (BT-010)](#5-기상청-날씨-데이터-수집-및-동기화-bt-010)
6. [대용량 처리 및 장애 격리 전략](#6-대용량-처리-및-장애-격리-전략)
7. [데이터베이스 스키마 (배치 연관)](#7-데이터베이스-스키마-배치-연관)
8. [Python 코드 스타일 가이드](#8-python-코드-스타일-가이드)
9. [프로젝트 관리 및 운영 가이드](#9-프로젝트-관리-및-운영-가이드)
10. [외부 API 연동 상세 스펙 및 보조 도구](#10-외부-api-연동-상세-스펙-및-보조-도구)

---

## 1. 배치 서비스 개요

Trp Batch 모듈은 **Python 비동기 환경**을 기반으로 구축된 데이터 파이프라인으로, **한국관광공사 TourAPI 공공데이터 수집**, **기상청 실시간 예보 동기화(3시간 주기)**, 그리고 **AI RAG 검색을 위한 날씨·계절 궁합 메타데이터 가공 및 벡터 임베딩(`pgvector`) 적재**를 전담합니다.

- **기반 기술**: Python (3.x), `asyncio`, `httpx` (비동기 HTTP), `SQLAlchemy` / `psycopg` (`pgvector` 연동), `APScheduler` / Cron (실제 프로젝트 의존성에 따름)
- **핵심 역할**:
  - 한국관광공사(TourAPI 4.0) 관광지, 문화시설, 행사/축제, 음식점, 숙박 데이터 주기적 동기화
  - 기상청 단기예보 격자 데이터 정기 수집 및 지역별 날씨 테이블 갱신
  - **관광지 상세 텍스트 + 실내외 구분 + 추천 날씨/계절 태그를 조합하여 벡터 임베딩 생성 후 `pgvector` 적재**
  - 조회 성능 최적화를 위한 인기 장소 랭킹 및 Redis 추천 캐시 생성

---

## 2. 배치 아키텍처 및 데이터 흐름

```mermaid
flowchart TD
    subgraph ExternalSources["외부 공공데이터 API"]
        TourAPI["한국관광공사 TourAPI 4.0<br/>(관광지/음식점/축제)"]
        KMA["기상청 날씨 API<br/>(단기예보 격자 데이터)"]
    end

    subgraph PythonBatch["Python Batch Pipeline (Async)"]
        AsyncCollector["1. 비동기 수집 파이프라인<br/>(httpx + asyncio: 페이징 수집)"]
        DataProcessor["2. 가공 & 태깅 파이프라인<br/>(실내/실외 분류, 날씨·계절 태그 결합)"]
        EmbeddingPipeline["3. 임베딩 파이프라인<br/>(Batch Embedding API 호출 - 100건 청크)"]
        BulkWriter["4. 대량 적재 엔진<br/>(SQLAlchemy Bulk Upsert)"]

        AsyncCollector --> DataProcessor --> EmbeddingPipeline --> BulkWriter
    end

    subgraph StorageLayer["데이터 영속화 & 캐싱"]
        PG[("PostgreSQL (RDBMS)<br/>- tour_places (장소 메타)<br/>- weather_forecast (날씨)")]
        PGV[("pgvector (Vector DB)<br/>- tour_embeddings (날씨·장소 벡터)")]
        RedisCache[("Redis Cache<br/>- 인기 장소 랭킹<br/>- 추천 후보 캐시")]
    end

    TourAPI --> AsyncCollector
    KMA --> AsyncCollector

    BulkWriter -->|"메타데이터 저장"| PG
    BulkWriter -->|"1536차원 벡터 저장"| PGV
    BulkWriter -->|"캐시 갱신"| RedisCache
```

---

## 3. 배치 작업(Job) 전체 명세 (BT-001 ~ BT-014)

| Batch ID | 작업(Job) 명칭 | 실행 주기 (Cron) | 작업 설명 | 입력(Source) | 결과(Target) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BT-001** | 지역 관광지 기본정보 적재 | 매일 02:00 (`0 2 * * *`) | 전국 시/도/구군별 관광지 목록 동기화 | TourAPI (areaBasedList2) | `tour_places` (RDBMS) |
| **BT-002** | 관광지 상세정보 적재 | 매일 02:30 (`30 2 * * *`) | 개요, 운영시간, 휴무일, 주차여부 동기화 | TourAPI (detailIntro2) | `tour_place_details` |
| **BT-003** | 음식점/카페 데이터 적재 | 매일 03:00 (`0 3 * * *`) | 지역별 맛집, 대표메뉴, 영업시간 동기화 | TourAPI (음식점 코드) | `tour_places` (식당/카페) |
| **BT-004** | 숙박 정보 적재 | 매일 03:30 (`30 3 * * *`) | 호텔, 펜션, 게스트하우스 정보 적재 | TourAPI (숙박 코드) | `tour_accommodations` |
| **BT-005** | 행사 및 축제 적재 | 매일 04:00 (`0 4 * * *`) | 진행 중/예정 축제 일정 및 장소 동기화 | TourAPI (searchFestival2) | `tour_festivals` |
| **BT-006** | 문화시설 적재 | 매일 04:30 (`30 4 * * *`) | 미술관, 박물관, 전시관 등 실내 시설 적재 | TourAPI (문화시설 코드) | `tour_places` (문화) |
| **BT-007** | 쇼핑/전통시장 적재 | 매일 05:00 (`0 5 * * *`) | 쇼핑몰, 전통시장, 복합문화몰 적재 | TourAPI (쇼핑 코드) | `tour_places` (쇼핑) |
| **BT-008** | 대표 이미지 동기화 | 매일 05:30 (`30 5 * * *`) | 원본/썸네일 이미지 URL 수집 및 유효성 검증 | TourAPI (detailImage2) | `tour_place_images` |
| **BT-009** | 폐업/삭제 데이터 동기화 | 매일 06:00 (`0 6 * * *`) | API에서 삭제된 장소 `is_deleted=true` 처리 | TourAPI 동기화 목록 | `tour_places` (상태값) |
| **BT-010** | **실시간 날씨 예보 갱신** | **매 3시간 주기 (`0 */3 * * *`)** | 전국 주요 관광 지역 단기예보 수집/갱신 | 기상청 단기예보 API | `weather_forecast` |
| **BT-011** | 계절/날씨 적합도 태깅 | 매일 06:30 (`30 6 * * *`) | 장소별 실내외 판별 및 어울리는 날씨 태그 생성 | 카테고리/개요 분석 | `tour_place_tags` |
| **BT-012** | **RAG 관광지 벡터 임베딩 적재** | **매일 07:00 (`0 7 * * *`)** | **날씨+계절+장소 텍스트 임베딩 생성 후 pgvector 적재** | 신규/수정된 장소 텍스트 | `tour_embeddings` (`pgvector`) |
| **BT-013** | 인기 장소 집계 및 캐시 | 매일 07:30 (`30 7 * * *`) | 일정 생성 빈도 기반 랭킹 계산 및 Redis 적재 | 사용자 일정 로그 | Redis (`RANKING:*`) |
| **BT-014** | 배치 실행 이력 저장 | 매 Job 실행 시 (`Logging`) | 수행 시간, 처리 건수, 실패 원인 로깅 | Execution Metadata | `batch_job_log` |

---

## 4. RAG 벡터 임베딩 생성 파이프라인 (핵심)

AI 서비스가 **날씨·계절에 최적화된 장소를 유사도 검색**할 수 있도록, 배치 모듈에서 **임베딩용 청크(Chunk) 텍스트를 정밀하게 조립**하여 벡터화합니다.

### 4.1 청크(Chunk) 텍스트 조립 템플릿
```python
def build_embedding_chunk(place: dict) -> str:
    indoor_text = "실내 공간으로 비, 눈, 무더위 등 궂은 날씨에도 쾌적하게 방문 가능" if place["is_indoor"] else "야외 명소로 맑은 날 야외 활동과 자연 풍경 감상에 적합"
    
    return f"""[장소명] {place['name']}
[지역] {place['region_name']} {place.get('sigungu_name', '')}
[카테고리] {place['category']} ({'실내' if place['is_indoor'] else '야외'})
[추천 날씨] {place.get('suitable_weather', '사계절 맑음')}
[추천 계절] {place.get('suitable_seasons', '사계절')}
[실내외 특성] {indoor_text}
[장소 설명] {place.get('overview', '')}
[운영 안내] 영업시간: {place.get('business_hours', '정보 없음')}, 휴무일: {place.get('holiday_info', '연중무휴')}
""".strip()
```

### 4.2 배치 임베딩 적재 처리 흐름
```text
1. [DB 조회]: PostgreSQL에서 '임베딩이 없거나', '정보가 수정(updated_at 변경)'된 장소를 100건 단위 페이징 조회
2. [텍스트 조립]: 개요, 카테고리, 휴무일 분석 ➡️ 실내/실외(is_indoor) 판별 후 템플릿 텍스트 생성
3. [Batch Embedding]: 임베딩 모델(OpenAI / bge-m3 / KoSimCSE)에 100개 문장을 한 번에 요청하여 1536차원 벡터 리스트 획득
4. [Bulk Upsert]: psycopg3 / SQLAlchemy를 사용하여 `tour_embeddings` 테이블에 배치 저장 (ON CONFLICT UPDATE)
```

---

## 5. 기상청 날씨 데이터 수집 및 동기화 (BT-010)

사용자가 여행을 계획할 때 당일의 날씨 조건을 제공하기 위해, 전국 주요 시/군/구의 날씨 예보를 3시간 간격으로 갱신합니다.

### 5.1 수집 대상 정보
- **강수 형태 (PTY)**: 없음(0), 비(1), 비/눈(2), 눈(3), 소나기(4)
- **하늘 상태 (SKY)**: 맑음(1), 구름많음(3), 흐림(4)
- **1시간 기온 (TMP)**: 섭씨 기온 (℃)
- **강수 확률 (POP)**: 강수 확률 (%)

### 5.2 날씨 표준화 코드 매핑
AI 파이프라인에서 직관적으로 사용할 수 있도록 표준 코드로 변환하여 저장합니다.

| 기상청 PTY / SKY | 변환 날씨 코드 | AI 매핑 키워드 |
| :--- | :--- | :--- |
| PTY = 1, 2, 4 | `RAIN` | "비 오는 날", "우천", "실내 추천" |
| PTY = 3 | `SNOW` | "눈 오는 날", "설경", "따뜻한 실내" |
| PTY = 0 & SKY = 1 | `SUNNY` | "맑은 날", "야외 활동", "전망 명소" |
| PTY = 0 & SKY >= 3 | `CLOUDY` | "흐린 날", "선선한 날씨", "산책/카페" |

---

## 6. 대용량 처리 및 장애 격리 전략

TourAPI의 데이터는 수만~수십만 건에 달하므로, Python 비동기 아키텍처를 활용하여 빠르고 안정적으로 완주할 수 있도록 전략을 수립합니다.

### 6.1 비동기 청크(Chunk) 처리 및 속도 제어
- `httpx.AsyncClient`와 `asyncio.Semaphore`를 사용하여 공공데이터 포털의 **초당 요청 제한(Rate Limit)을 준수**하면서도 병렬 수집 속도를 극대화합니다.
- 배치 DB 삽입 시 `session.execute(insert().on_conflict_do_update())`를 사용하여 대량 데이터를 100건씩 Bulk 처리합니다.

### 6.2 Skip & Retry 정책 (오류 격리)
- **Tenacity 기반 자동 재시도**: 외부 API 일시적 타임아웃 발생 시 지수 백오프(Exponential Backoff)를 적용하여 최대 3회 재시도합니다.
- **단건 에러 격리(Skip)**: 특정 데이터의 위경도 누락 또는 JSON 파싱 오류 발생 시, 해당 레코드만 `ERROR` 로깅 후 스킵하고 전체 잡은 계속 진행합니다.

### 6.3 증분 업데이트 (Incremental Sync)
- 매번 전체 수만 건을 다시 임베딩하면 API 비용과 시간이 크게 낭비됩니다.
- TourAPI의 수정일자(`modifiedtime`)와 당사 DB의 `updated_at`을 비교하여, **신규 등록되었거나 수정된 장소만 선별하여 임베딩을 수행**합니다.

---

## 7. 데이터베이스 스키마 (배치 연관)

### 7.1 장소 메타데이터 테이블 (`tour_places`)
```sql
CREATE TABLE tour_places (
    id BIGSERIAL PRIMARY KEY,
    content_id VARCHAR(50) UNIQUE NOT NULL, -- TourAPI 고유 ID
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,          -- TOUR, RESTAURANT, CULTURE, CAFE 등
    region_code VARCHAR(20) NOT NULL,       -- PUSAN, JEJU, SEOUL 등
    address VARCHAR(255),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    is_indoor BOOLEAN DEFAULT false,        -- 실내 여부
    business_hours TEXT,
    holiday_info VARCHAR(255),
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.2 RAG 벡터 임베딩 테이블 (`tour_embeddings`)
```sql
-- pgvector 확장 활성화 필요: CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE tour_embeddings (
    place_id BIGINT PRIMARY KEY REFERENCES tour_places(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,               -- 임베딩에 사용된 통합 텍스트
    embedding vector(1536) NOT NULL,        -- 1536차원 벡터 데이터
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 인덱스 생성 (고속 코사인 유사도 검색용)
CREATE INDEX idx_tour_embeddings_hnsw 
ON tour_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

### 7.3 기상청 날씨 예보 테이블 (`weather_forecast`)
```sql
CREATE TABLE weather_forecast (
    id BIGSERIAL PRIMARY KEY,
    region_code VARCHAR(20) NOT NULL,
    forecast_date DATE NOT NULL,
    condition_code VARCHAR(20) NOT NULL,    -- RAIN, SUNNY, CLOUDY, SNOW
    temperature DOUBLE PRECISION,
    precipitation_prob INT,                 -- 강수확률 (%)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_region_date UNIQUE (region_code, forecast_date)
);
```

---

## 8. Python 코드 스타일 가이드

배치 모듈은 Python 3.11+ 기반으로 개발되며, 대용량 데이터를 안전하게 처리하기 위해 아래의 코딩 컨벤션을 엄격히 준수합니다.

### 8.1 포매팅 및 린팅 표준
- **표준 도구**: PEP 8 준수, **Ruff** (린터 및 포매터 통합) 또는 **Black + Flake8** 사용
- **최대 줄 길이(Line Length)**: `100자`
- **들여쓰기**: 공백 4칸(Soft Tabs, Spaces)

### 8.2 타입 힌팅 (Type Hinting) 필수화
모든 함수의 인자와 반환값에는 명시적인 Type Hint를 작성합니다.
```python
from typing import List, Dict, Any, Optional

async def fetch_tour_places(
    area_code: str,
    page_no: int = 1,
    num_of_rows: int = 100
) -> List[Dict[str, Any]]:
    """TourAPI로부터 지역별 관광지 목록을 비동기 조회합니다."""
    ...
```

### 8.3 데이터 모델링 (Pydantic / Dataclasses)
- 수집된 원시(Raw) 데이터의 구조를 정의하고 유효성 검증을 수행하기 위해 Pydantic 모델을 사용합니다.
- DB 엔티티 매핑은 SQLAlchemy 2.0 `Mapped` 스타일을 준수합니다.

### 8.4 네이밍 컨벤션
- **모듈/스크립트명**: `snake_case` (예: `sync_tour_places.py`, `sync_weather.py`)
- **클래스명**: `PascalCase` (예: `TourApiClient`, `EmbeddingPipeline`)
- **함수/변수명**: `snake_case` (예: `build_chunk()`, `chunk_size`)
- **상수명**: `UPPER_SNAKE_CASE` (예: `BATCH_SIZE = 100`, `MAX_RETRIES = 3`)

### 8.5 로깅 및 예외 처리 원칙
- `print()` 사용을 엄격히 금지하며, `logging` 또는 `loguru`를 사용하여 시간, 로그 레벨, Job ID가 포함된 구조화된 로그를 남깁니다.
- 재시도 불가능한 에러(DB 연결 불가 등)는 즉시 예외를 발생시키고, 개별 아이템 파싱 오류는 `logger.warning()` 기록 후 스킵합니다.

---

## 9. 프로젝트 관리 및 운영 가이드

### 9.1 패키지 디렉터리 구조
```text
tour-batch/
├── jobs/                    # 배치 실행 단위 스크립트
│   ├── sync_tour.py         # 관광지/음식점/축제 수집 Job
│   ├── sync_weather.py      # 기상청 날씨 동기화 Job
│   └── sync_embeddings.py   # RAG 벡터 임베딩 생성 Job
├── clients/                 # 외부 API 연동 클라이언트 (TourAPI, KMA, LLM Embedding)
├── db/                      # SQLAlchemy 모델, DB 커넥션 풀, 세션 관리
├── pipelines/               # 데이터 정제, 실내외 태깅, 청크 가공 로직
├── utils/                   # 격자 좌표 변환, 날짜 헬퍼
├── scheduler.py             # APScheduler 기반 정기 실행 진입점
├── requirements.txt         # 의존성 패키지 목록
├── Dockerfile               # 도커 배포 파일
└── tests/                   # pytest 단위 테스트
```

### 9.2 의존성 관리 및 가상환경
```bash
# 가상환경 구성
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 로컬 단일 잡 수동 테스트 실행
python -m jobs.sync_weather --date 2026-10-22
```

### 9.3 장애 알림 및 모니터링 (Slack 연동)
- 잡 실행 완료 또는 에러 발생 시 Slack Webhook을 통해 실행 통계(성공 건수, 실패 건수, 소요 시간)를 자동 전송합니다.

### 9.4 Git 브랜치 전략 및 네이밍 규칙

배치 모듈의 기능 개발 및 수정 시 아래의 브랜치 네이밍 컨벤션(`접두사/티켓번호-작업내용`)을 준수합니다:

| 접두사 (Type) | 사용 목적 | 브랜치 네이밍 예시 |
| :--- | :--- | :--- |
| `feat` | 신규 수집 Job, 날씨 동기화 스케줄러 구현 | `feat/TOUR-15-sync-weather-job` |
| `fix` | TourAPI 응답 파싱 에러, DB Upsert 충돌 수정 | `fix/TOUR-19-tourapi-parse-error` |
| `refactor` | 비동기 Chunk 처리 속도 개선, Semaphore 튜닝 | `refactor/TOUR-26-chunk-upsert-opt` |
| `docs` | BATCH.md 명세서 갱신 및 API 규격 업데이트 | `docs/TOUR-32-update-batch-spec` |

---

### 9.5 Git PR(Pull Request) 작성 표준 및 AI 리뷰어 가이드
- **PR 템플릿 Self-Check**:
  - [ ] 외부 API 호출 시 타임아웃 및 Semaphore 제한이 적용되었는가?
  - [ ] 대용량 DB 저장 시 Chunk Upsert 방식을 사용했는가?
  - [ ] 단건 에러 발생 시 전체 배치가 비정상 종료되지 않도록 예외가 격리되었는가?
- **AI 리뷰어 체크 포인트 (Review Point)**: "비동기 HTTP 커넥션 누수 여부", "API Rate Limit 초과 위험성" 중점 확인

---

## 10. 외부 API 연동 상세 스펙 및 보조 도구

AI 또는 개발자가 실제 연동 코드를 구현할 때 혼선 없이 즉시 호출할 수 있도록 공공데이터의 정확한 스펙과 변환 도구를 명시합니다.

### 10.1 한국관광공사 TourAPI 4.0 호출 규격
- **Base URL**: `https://apis.data.go.kr/B551011/KorService1`
- **공통 필수 파라미터**:
  - `serviceKey`: 공공데이터포털 인코딩/디코딩 API Key
  - `MobileOS`: `ETC`
  - `MobileApp`: `Trp`
  - `_type`: `json`
  - `numOfRows`: `100` (최대 100건 페이징)
  - `pageNo`: `1` ~ `N`

#### 콘텐츠 타입 ID (`contentTypeId`) 매핑 기준
| contentTypeId | 분류 명칭 | 대상 Job | 비고 |
| :--- | :--- | :--- | :--- |
| `12` | 관광지 (Tour Spot) | BT-001 | 산, 해변, 공원, 유적지 등 |
| `14` | 문화시설 (Culture) | BT-006 | 박물관, 미술관, 전시관 등 (실내 위주) |
| `15` | 축제/공연/행사 (Festival) | BT-005 | 기간 한정 축제 |
| `28` | 레포츠 (Leisure) | BT-001 | 액티비티, 스키, 해양스포츠 |
| `32` | 숙박 (Accommodation) | BT-004 | 호텔, 펜션, 게스트하우스 |
| `38` | 쇼핑 (Shopping) | BT-007 | 전통시장, 쇼핑몰, 면세점 |
| `39` | 음식점/카페 (Restaurant) | BT-003 | 맛집, 카페, 베이커리 |

#### 응답 JSON 기본 구조 및 좌표 매핑
```json
{
  "response": {
    "header": { "resultCode": "0000", "resultMsg": "OK" },
    "body": {
      "items": {
        "item": [
          {
            "contentid": "126508",
            "title": "해운대해수욕장",
            "contenttypeid": "12",
            "addr1": "부산광역시 해운대구 해운대해변로 264",
            "mapx": "129.158508", // ⭐️ 경도 (longitude)
            "mapy": "35.158698",  // ⭐️ 위도 (latitude)
            "firstimage": "http://tong.visitkorea.or.kr/...",
            "modifiedtime": "20261015143000"
          }
        ]
      },
      "totalCount": 2450
    }
  }
}
```

---

### 10.2 기상청 단기예보 API 규격 및 격자(nx, ny) 변환기

- **Base URL**: `https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst`
- **발표 시각 규칙 (`base_time`)**: `0200`, `0500`, `0800`, `1100`, `1400`, `1700`, `2000`, `2300` (매 3시간 단위 발표, 발표 후 약 10분 뒤 데이터 생성)

#### 위도/경도 ➡️ 기상청 격자(nx, ny) 변환 함수 (Python)
기상청 Lambert Conformal Conic 투영 공식에 맞춘 정확한 변환 스크립트입니다:

```python
import math

def convert_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """위도/경도를 기상청 격자 x, y 좌표로 변환합니다."""
    RE = 6371.00877     # 지구 반경(km)
    GRID = 5.0          # 격자 간격(km)
    SLAT1 = 30.0        # 투영 위도1(degree)
    SLAT2 = 60.0        # 투영 위도2(degree)
    OLON = 126.0        # 기준점 경도(degree)
    OLAT = 38.0         # 기준점 위도(degree)
    XO = 43             # 기준점 X좌표(GRID)
    YO = 136            # 기준점 Y좌표(GRID)

    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(math.floor(ra * math.sin(theta) + XO + 0.5))
    ny = int(math.floor(ro - ra * math.cos(theta) + YO + 0.5))
    return nx, ny

# 사용 예시: 부산 해운대 (위도 35.1587, 경도 129.1585) -> (98, 76)
```

---

### 10.3 공통 표준 ENUM 및 `.env` 규격

```python
from enum import Enum

class CategoryType(str, Enum):
    TOUR_SPOT = "TOUR_SPOT"         # 12
    CULTURE = "CULTURE"             # 14
    FESTIVAL = "FESTIVAL"           # 15
    LEISURE = "LEISURE"             # 28
    ACCOMMODATION = "ACCOMMODATION" # 32
    SHOPPING = "SHOPPING"           # 38
    RESTAURANT = "RESTAURANT"       # 39

class WeatherCondition(str, Enum):
    SUNNY = "SUNNY"     # 맑음
    RAIN = "RAIN"       # 비 (강수)
    CLOUDY = "CLOUDY"   # 흐림 / 구름많음
    SNOW = "SNOW"       # 눈
```

#### `.env.example`
```env
# Database Settings
DATABASE_URL=postgresql+psycopg://tour_admin:tour_password@localhost:5432/tour_db
REDIS_URL=redis://:tour_redis_pass@localhost:6379/0

# Public APIs
TOUR_API_KEY=your_tour_api_service_key_here
KMA_API_KEY=your_kma_weather_api_key_here

# Embedding API
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-3-small
```

---

> 💡 **연관 문서**:
> - RAG 검색 쿼리 및 동선 빌드 엔진: [AI.md](./AI.md)
> - 백엔드 멀티모듈 및 REST API 명세: [BACKEND.md](./BACKEND.md)
