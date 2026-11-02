# 🧠 Trp AI Service Specification (AI.md)
> **날씨·계절 기반 RAG(Vector DB) 시맨틱 검색 및 지능형 여행 동선 최적화 엔진**

```markdown
# 🔗 AI 서비스 Git 저장소 (Repository URL)
GIT_AI_REPO="https://github.com/<ORGANIZATION_OR_USER>/trp-ai"
```

---

## 📌 목차
1. [AI 서비스 개요](#1-ai-서비스-개요)
2. [전체 AI 파이프라인 아키텍처](#2-전체-ai-파이프라인-아키텍처)
3. [RAG 기반 날씨·계절 시맨틱 장소 추출 (1단계)](#3-rag-기반-날씨계절-시맨틱-장소-추출-1단계)
4. [지리적 위경도 기반 동선 최적화 (2단계)](#4-지리적-위경도-기반-동선-최적화-2단계)
5. [LLM 기반 맞춤형 일정 코스 빌드 (3단계)](#5-llm-기반-맞춤형-일정-코스-빌드-3단계)
6. [프롬프트 엔지니어링 규격](#6-프롬프트-엔지니어링-규격)
7. [REST API 인터페이스 명세 (Backend ↔ AI)](#7-rest-api-인터페이스-명세-backend--ai)
8. [날씨 변화 대응 실시간 재추천 (Rescheduling)](#8-날씨-변화-대응-실시간-재추천-rescheduling)
9. [로컬 LLM 및 서빙 환경 구성](#9-로컬-llm-및-서빙-환경-구성)
10. [Python 코드 스타일 및 로깅 가이드](#10-python-코드-스타일-및-로깅-가이드)
11. [프로젝트 관리 및 협업 가이드](#11-프로젝트-관리-및-협업-가이드)
12. [환경변수 및 모델 주입 규격 (.env)](#12-환경변수-및-모델-주입-규격-env)

---

## 1. AI 서비스 개요

Trp AI 엔진은 백엔드로부터 여행 조건(지역, 날짜, 취향 등)과 해당 일자의 기상 예보 데이터를 전달받아, **Vector DB(`pgvector`)에서 날씨·계절 궁합이 가장 뛰어난 장소를 시맨틱 유사도로 추출**하고, 이를 **지리적 동선 최적화 알고리즘 및 LLM**과 결합하여 완성형 일정 JSON을 생성하는 지능형 마이크로서비스입니다.

### 🔍 임베딩 모델 vs LLM 모델의 역할 분담 (핵심 원리)
> **Q. 임베딩 모델만으로 경로(동선/시간표)를 직접 받을 수 있나요?**
> **A. 불가능합니다.** 임베딩 모델과 LLM은 맡은 역할이 근본적으로 다릅니다:

| 구분 | 임베딩 모델 (Embedding Model) | 동선 최적화 알고리즘 (Router) | LLM 모델 (Large Language Model) |
| :--- | :--- | :--- | :--- |
| **핵심 역할** | **장소 검색 및 추출 (Retrieval)** | **물리적 이동 순서 정렬 (Routing)** | **코스 완성 및 시간표 빌드 (Generation)** |
| **동작 원리** | 텍스트를 숫자 벡터로 변환하여 Vector DB에서 유사도 검색 | 위경도 좌표 간 거리 행렬 계산 (TSP 최단거리) | 장소들을 맥락에 맞춰 배치하고 추천 사유 작성 |
| **산출물** | 날씨/계절에 어울리는 후보 장소 리스트 (Top-K) | 지그재그 이동 없는 순회 순서 | 시간대별 일정, 날씨 꿀팁이 담긴 최종 JSON |
| **필요 여부** | **필수 (장소 후보군 추출용)** | **권장 (좌표 오차 방지용)** | **필수 (일정 완성 및 JSON 파싱용)** |

- **도입 모델 (환경변수를 통해 유연하게 주입/변경 가능)**:
  - **임베딩 모델**: OpenAI (`text-embedding-3-small` 등) 또는 로컬/오픈소스 (`bge-m3`, `KoSimCSE` 등)
  - **LLM 모델**: Ollama 로컬 LLM (`Llama 3`, `Qwen` 등) 또는 클라우드 API (`Gemini`, `OpenAI` 등)

---

## 2. 전체 AI 파이프라인 아키텍처

AI 서비스는 단일 LLM 호출의 한계(지리적 거리 계산 오차, 환각 등)를 극복하기 위해 **[장소 추출 ➡️ 동선 계산 ➡️ 일정 생성]**의 3단계 파이프라인으로 동작합니다.

```mermaid
flowchart TD
    subgraph Input["1. 입력 (Backend -> AI)"]
        Req["여행 요청<br/>(지역: 부산, 일정: 2박 3일, 테마: 힐링)"]
        Weather["날씨/계절 메타데이터<br/>(1일차: 우천 16℃, 계절: 가을)"]
    end

    subgraph Step1["2. [1단계] RAG 장소 추출 (Retrieval)"]
        QueryBuilder["날씨·계절 시맨틱 쿼리 빌더"]
        VDB[("pgvector<br/>(장소 특성 + 날씨/계절 태그)")]
        TopPlaces["Top-K 후보 장소 추출<br/>(우천 특화 실내/오션뷰 카페/미술관)"]
        QueryBuilder -->|"코사인 유사도 검색"| VDB
        VDB --> TopPlaces
    end

    subgraph Step2["3. [2단계] 동선 최적화 (Routing)"]
        CoordSort["위경도 좌표 기반 거리 행렬 계산"]
        TimeFilter["운영시간 / 휴무일 / 식사시간 검증"]
        OptimalRoute["지그재그 방지 1차 정렬 코스"]
        CoordSort --> TimeFilter --> OptimalRoute
    end

    subgraph Step3["4. [3단계] 코스 빌드 (Generation)"]
        PromptGen["System / User 프롬프트 조합"]
        LLM["Ollama (Llama 3) / Gemini"]
        ScheduleJSON["구조화된 여행 일정 JSON<br/>(시간대별 장소, 이동경로, 날씨 맞춤 팁)"]
        PromptGen --> LLM --> ScheduleJSON
    end

    Input --> Step1
    TopPlaces --> Step2
    OptimalRoute --> Step3
    ScheduleJSON -->|"REST API 반환"| Output["5. Backend 저장 & 카카오맵 서빙"]
```

---

## 3. RAG 기반 날씨·계절 시맨틱 장소 추출 (1단계)

### 3.1 검색 쿼리(Query) 생성 원리
AI 서비스는 전달받은 날씨와 계절 정보를 결합하여 벡터 검색에 최적화된 시맨틱 문장을 동적으로 생성합니다.

- **우천 시 쿼리 예시**:
  > *"부산에서 비 오는 쌀쌀한 가을날에 방문하기 좋은 실내 힐링 명소, 비 내리는 풍경이 보이는 대형 카페, 미술관, 쾌적한 실내 복합문화공간"*
- **맑은 날 쿼리 예시**:
  > *"부산에서 맑고 선선한 가을 날씨를 만끽할 수 있는 야외 산책로, 억새 명소, 전망 좋은 해안가 코스"*

### 3.2 pgvector 하이브리드 검색 쿼리
순수 벡터 유사도 검색과 함께, 강우 시 야외 장소 배제를 위한 **메타데이터 하이브리드 필터링**을 적용합니다.

```sql
-- 비 올 때: 실내(is_indoor=true) 우선 가중치 + 시맨틱 유사도 검색
SELECT 
    p.id,
    p.name,
    p.category,
    p.latitude,
    p.longitude,
    p.business_hours,
    1 - (p.embedding <=> :query_vector) AS similarity
FROM tour_places p
WHERE p.region_code = :regionCode
  AND (:isRain = false OR p.is_indoor = true)
ORDER BY similarity DESC
LIMIT 25;
```

---

## 4. 지리적 위경도 기반 동선 최적화 (2단계)

LLM은 텍스트 추론에는 강하나 숫자로 된 지리 좌표 계산(최단 거리, TSP)에서 비효율적인 동선(동쪽 ➡️ 서쪽 ➡️ 다시 동쪽)을 만들 수 있습니다. 이를 방지하기 위해 **알고리즘 기반 지리 정렬**을 선행합니다.

### 4.1 처리 로직
1. **클러스터링 및 권역 분할**: 일정 일자(Day 1, Day 2 등)에 맞춰 인접한 좌표끼리 장소를 1차 군집화(K-Means 또는 근접 격자)
2. **외판원 문제(TSP) 단순화 정렬**:
   - 숙소 또는 시작 지점(역/공항)을 기준으로 유클리디안 거리/하버사인 공식을 이용해 최단 순회 경로 산출
3. **제약 조건 필터링**:
   - `filterBusinessHours()`: 방문 예상 시간대에 개점 중인지 확인
   - `filterHoliday()`: 당일 휴무일 장소 자동 제외
   - `filterDuplicateCategory()`: 연속으로 카페 2곳 또는 식당 2곳이 이어지지 않도록 슬롯 배분

---

## 5. LLM 기반 맞춤형 일정 코스 빌드 (3단계)

지리적으로 정렬된 후보 장소 목록을 바탕으로, LLM이 여행자의 페르소나와 날씨 상황에 맞춘 **스토리텔링형 시간표와 이동 팁을 포함한 완성형 JSON**을 완성합니다.

### 5.1 생성 결과 규격 (JSON Output)
```json
{
  "tripName": "비 오는 가을 부산 감성 힐링 1일 코스",
  "weatherSummary": "강수확률 80% 우천 예보로 전 일정 실내 문화 및 오션뷰 카페 중심 구성",
  "dailySchedules": [
    {
      "day": 1,
      "date": "2026-10-25",
      "weatherCondition": "RAIN",
      "places": [
        {
          "step": 1,
          "placeId": 1024,
          "placeName": "SEA LIFE 부산아쿠아리움",
          "category": "INDOOR_EXHIBITION",
          "startTime": "10:30",
          "endTime": "12:30",
          "stayTimeMinutes": 120,
          "latitude": 35.1593,
          "longitude": 129.1611,
          "reason": "오전 비 예보에 맞춰 비를 맞지 않고 쾌적하게 관람할 수 있는 실내 코스로 선정했습니다."
        },
        {
          "step": 2,
          "placeId": 2048,
          "placeName": "해운대 기와집 대구탕",
          "category": "RESTAURANT",
          "startTime": "12:45",
          "endTime": "13:45",
          "stayTimeMinutes": 60,
          "latitude": 35.1612,
          "longitude": 129.1752,
          "reason": "아쿠아리움에서 차로 5분 거리이며, 쌀쌀한 비 오는 날 따뜻한 국물 요리를 즐기기 제격입니다."
        },
        {
          "step": 3,
          "placeId": 3072,
          "placeName": "달맞이길 랑데자뷰 카페",
          "category": "CAFE",
          "startTime": "14:00",
          "endTime": "15:30",
          "stayTimeMinutes": 90,
          "latitude": 35.1585,
          "longitude": 129.1820,
          "reason": "통창 너머로 비 내리는 해운대 바다를 감상하며 여유로운 티타임을 보낼 수 있습니다."
        }
      ]
    }
  ]
}
```

---

## 6. 프롬프트 엔지니어링 규격

### 6.1 System Prompt
```text
당신은 대한민국 최고의 AI 여행 플래너 "Trp Engine"입니다.
주어진 장소 후보군과 여행 조건, 당일 기상청 날씨/계절 정보를 종합 분석하여, 
여행자가 지치지 않고 날씨를 즐길 수 있는 최적의 시간대별 여행 일정을 설계해야 합니다.

[작성 원칙]
1. 반드시 전달받은 후보 장소 목록(Candidate Places) 내에서만 선택하십시오. (환각 금지)
2. 날씨가 우천(RAIN)일 경우 반드시 실내 장소 및 비 풍경이 좋은 장소 위주로 배치하고, 추천 사유에 날씨 팁을 명시하십시오.
3. 점심 시간(12:00~13:30)과 저녁 시간(18:00~19:30)에는 반드시 음식점이 배치되어야 합니다.
4. 출력 형식은 다른 설명 없이 반드시 순수한 JSON 형식만 반환하십시오.
```

### 6.2 User Prompt 빌더 구조
- `appendWeatherInfo()`: 날씨 상태(비, 맑음, 기온) 주입
- `appendSeasonInfo()`: 계절(봄, 여름, 가을, 겨울) 특성 주입
- `appendPlaceInfo()`: 2단계에서 정렬된 후보 장소(ID, 이름, 좌표, 실내여부, 설명) 주입
- `appendTravelCondition()`: 인원수, 여행자 취향(힐링/체험/미식), 이동 수단(대중교통/자가용) 주입

---

## 7. REST API 인터페이스 명세 (Backend ↔ AI)

### 7.1 신규 여행 일정 생성
- **Endpoint**: `POST /api/v1/ai/schedule`
- **Request Body**:
```json
{
  "regionCode": "PUSAN",
  "startDate": "2026-10-25",
  "endDate": "2026-10-26",
  "theme": "HEALING",
  "transportation": "PUBLIC",
  "dailyWeathers": [
    {
      "date": "2026-10-25",
      "condition": "RAIN",
      "temp": 16,
      "precipitationProbability": 80
    },
    {
      "date": "2026-10-26",
      "condition": "SUNNY",
      "temp": 20,
      "precipitationProbability": 10
    }
  ]
}
```
- **Response**: `200 OK` (상단 5.1 JSON 포맷 규격)

### 7.2 실시간 대체 일정 재추천 (Reschedule)
- **Endpoint**: `POST /api/v1/ai/reschedule`
- **설명**: 기상 악화(맑음 ➡️ 비) 또는 특정 장소 취소 시 대체 장소를 Vector DB에서 즉시 재추출하여 동선 재조정

---

## 8. 날씨 변화 대응 실시간 재추천 (Rescheduling)

```mermaid
sequenceDiagram
    autonumber
    actor User as 여행자
    participant BE as Backend
    participant AI as AI Engine
    participant VDB as Vector DB

    User->>BE: 갑작스런 폭우로 야외 일정 대체 요청
    BE->>AI: 재추천 요청 (현재 위치 좌표 + 변경 날씨: RAIN)
    AI->>VDB: 현재 위치 반경 5km 내 실내 장소(is_indoor=true) 벡터 쿼리
    VDB-->>AI: 최적 실내 대체 장소 3곳 반환
    AI->>AI: 기존 다음 동선과 연결되는 최단 경로 재계산
    AI-->>BE: 갱신된 일정 JSON 반환
    BE-->>User: 카카오맵 마커/동선 실시간 변경 표시
```

---

## 9. 로컬 LLM 및 서빙 환경 구성

### 9.1 Ollama 컨테이너 기반 로컬 서빙
`docker-compose.yml`을 통해 로컬 개발 시 GPU/CPU 환경에서 Ollama를 실행합니다.

```bash
# Ollama 모델 풀(Pull)
docker exec -it tour_ollama ollama pull llama3:8b

# 로컬 프롬프트 테스트
curl http://localhost:11434/api/generate -d '{
  "model": "llama3:8b",
  "prompt": "비 오는 부산 여행 코스를 추천해줘",
  "stream": false
}'
```

---

## 10. Python 코드 스타일 및 로깅 가이드

AI 서비스 모듈은 Python 3.x 비동기 환경에서 동작하며, 프로덕션 레벨의 코드 가독성, 타입 안정성, 그리고 모니터링 가능성(Observability)을 확보하기 위해 아래 기준을 엄격히 준수합니다.

---

### 10.1 포매팅 및 린팅 표준
- **표준 도구**: PEP 8 준수, **Ruff** (린터 및 포매터 통합) 또는 **Black + isort + Flake8** 사용
- **최대 줄 길이(Line Length)**: `100자`
- **들여쓰기**: 공백 4칸(Soft Tabs, Spaces)
- **Import 정렬 순서 (isort 규격)**:
  1. 표준 라이브러리 (`import math`, `import asyncio`, `from typing import ...`)
  2. 서드파티 라이브러리 (`from fastapi import ...`, `from pydantic import ...`, `from loguru import logger`)
  3. 로컬 프로젝트 모듈 (`from app.core.config import settings`, `from app.models.dto import ...`)

---

### 10.2 타입 힌팅 및 Docstring (Google Style)
모든 함수의 인자와 반환값에는 명시적인 Type Hint와 의도를 설명하는 Google Style Docstring을 작성합니다.

```python
from typing import List, Dict, Any

async def search_candidate_places(
    region_code: str,
    query_vector: List[float],
    is_rain: bool = False,
    top_k: int = 20
) -> List[Dict[str, Any]]:
    """날씨 및 계절 벡터 기반으로 pgvector에서 후보 장소를 추출합니다.

    Args:
        region_code: 조회할 지역 코드 (예: "PUSAN", "JEJU")
        query_vector: 1536차원 임베딩 쿼리 실수 리스트
        is_rain: 우천 여부 (True일 경우 실내 장소 우선 필터링)
        top_k: 최대 반환 장소 개수

    Returns:
        코사인 유사도 순으로 정렬된 후보 장소 딕셔너리 리스트

    Raises:
        DatabaseConnectionError: pgvector DB 연결 실패 시 발생
    """
    ...
```

---

### 10.3 Pydantic v2 기반 DTO 모델링 & 네이밍
- **클래스명**: `PascalCase` (예: `TripScheduleRequest`, `PlaceDetailDto`)
- **함수/변수명**: `snake_case` (예: `calculate_distance()`, `optimal_route`)
- **상수명**: `UPPER_SNAKE_CASE` (예: `DEFAULT_TOP_K = 20`, `MAX_RETRIES = 3`)
- **DTO 불변성**: 중요한 DTO는 `model_config = ConfigDict(frozen=True)`를 적용하여 사이드 이펙트 방지

---

### 10.4 표준 로깅(Logging) 가이드 ⭐️

AI 서비스는 비동기 호출 및 LLM 지연시간(Latency), 프롬프트 토큰을 실시간 추적해야 하므로 **`loguru` 기반의 구조화된 로깅**을 표준으로 채택합니다.

#### 1) 표준 로그 포맷
```text
[TIMESTAMP] | [LEVEL] | [MODULE:LINE] | [REQ_ID] - MESSAGE | extra_fields
```
- **실제 출력 예시**:
```text
2026-10-22 14:30:15.123 | INFO     | rag.search:search_places:45 | [req_id=a1b2c3] - RAG 장소 추출 완료 | region=PUSAN, count=20, latency_ms=42.5, top_similarity=0.884
```

#### 2) 로그 레벨별 사용 원칙
| 로그 레벨 | 사용 시점 및 대상 | 예시 |
| :--- | :--- | :--- |
| `DEBUG` | 개발 및 디버깅용 상세 데이터 | LLM 원본 프롬프트 내용, 벡터 유사도 상위 5개 점수 |
| `INFO` | 주요 비즈니스 마일스톤 완료 | API 요청 수신, RAG 검색 완료, LLM 일정 생성 완료 |
| `WARNING` | 정상 흐름이나 주의/보정 발생 | 실내 대체 장소 부족으로 2순위 검색, LLM JSON 파싱 1회 재시도 |
| `ERROR` | 비즈니스 로직 중단 및 예외 발생 | pgvector 쿼리 실패, LLM 응답 타임아웃, 포맷 불일치 예외 |

#### 3) LLM & RAG 전용 로깅 컨벤션
LLM 호출 시에는 비용과 성능 측정을 위해 **반드시 토큰 수와 수행 시간(ms)**을 기록합니다:
```python
logger.info(
    "LLM 일정 생성 완료 | model={}, prompt_tokens={}, completion_tokens={}, latency_ms={:.2f}",
    settings.LLM_MODEL_NAME,
    usage.prompt_tokens,
    usage.completion_tokens,
    duration_ms
)
```

#### 4) 로깅 금지 및 보안 규칙
- **개인정보(PII) 출력 금지**: 사용자 연락처, 이메일 등 개인정보를 로그에 평문 출력 금지
- **API Key 마스킹**: OpenAI Key, Gemini Key 등은 앞 4자리 외 마스킹 (`sk-proj-****`)
- **`print()` 절대 사용 금지**: 디버깅용 `print()`는 커밋 전 전면 제거하고 오직 `logger`만 사용

---

### 10.5 로거 설정 및 사용 예제 코드 스니펫
```python
import sys
from loguru import logger
from app.core.config import settings

def setup_logger():
    """애플리케이션 전역 로거를 초기화합니다."""
    logger.remove() # 기본 핸들러 제거
    
    # 콘솔 출력 포맷 설정
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<magenta>[{extra[request_id]}]</magenta> - <level>{message}</level>"
    )
    logger.add(sys.stdout, format=log_format, level="INFO", colorize=True)
    
    # 프로덕션 파일 로깅 (JSON 포맷, 500MB 단위 로테이션)
    logger.add(
        "logs/ai_service_{time:YYYY-MM-DD}.log",
        rotation="500 MB",
        retention="14 days",
        level="INFO",
        serialize=True # ELK/CloudWatch 수집용 JSON 로깅
    )

# 비즈니스 로직에서의 사용
# logger.bind(request_id="req_98765").info("여행 일정 생성 시작")
```

---

## 11. 프로젝트 관리 및 협업 가이드

### 11.1 디렉터리 구조 표준
```text
ai-service/
├── app/
│   ├── api/               # FastAPI / REST 라우터 (Endpoints)
│   ├── core/              # 설정(config), 로깅, 공통 예외
│   ├── models/            # Pydantic DTO 및 내부 스키마
│   ├── rag/               # Vector DB 쿼리, 청크 임베더, 프롬프트 빌더
│   ├── router/            # 2단계 지리적 동선 최적화 알고리즘
│   ├── services/          # 일정 생성 종합 오케스트레이션 로직
│   └── main.py            # 앱 실행 진입점
├── tests/                 # pytest 단위 및 통합 테스트
├── scripts/               # 프롬프트 벤치마크 및 A/B 테스트 스크립트
├── Dockerfile
├── requirements.txt       # 의존성 패키지 목록
└── README.md
```

### 11.2 의존성 관리 및 가상환경
- Python 3.11 가상환경(`venv`) 격리 사용:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

### 11.3 테스트 및 RAG 품질 검증
- **단위 테스트**: `pytest tests/` (각 컴포넌트별 로직 검증)
- **RAG 정밀도 검증 (Recall & Hallucination Check)**:
  - 프롬프트 변경 시, `tests/test_prompt_evaluation.py`를 실행하여 "우천 시 실내 장소 포함 비율", "출력 JSON 스키마 준수율"을 사전 검증 후 머지합니다.

### 11.4 Git 브랜치 전략 및 네이밍 규칙

배치 및 공통 협업 규격을 준수하여, AI 서비스 모듈의 브랜치는 Git Flow 변형 모델과 Conventional 네이밍을 따릅니다.

#### 1) 브랜치 생명주기
- **`main`**: 프로덕션 운영 환경 배포 브랜치 (항상 안정적인 상태 유지)
- **`develop`**: 개발 및 통합 테스트 기준 브랜치 (모든 기능 브랜치의 베이스)
- **`feat/`**, **`fix/`**, **`refactor/`**: 단위 작업 브랜치 (`develop`에서 분기 후 `develop`으로 PR 제출)

#### 2) 브랜치 타입별 네이밍 컨벤션 (`접두사/티켓번호-작업내용`)
| 접두사 (Type) | 사용 목적 | 브랜치 네이밍 예시 |
| :--- | :--- | :--- |
| `feat` | 신규 프롬프트, RAG 검색 로직, 신규 API 구현 | `feat/TOUR-12-prompt-builder` |
| `fix` | LLM JSON 파싱 오류, 벡터 차원 불일치 등 버그 수정 | `fix/TOUR-18-llm-json-parse-error` |
| `refactor` | 벡터 검색 성능 최적화, 프롬프트 경량화, 비동기 개선 | `refactor/TOUR-25-vector-search-perf` |
| `docs` | AI.md 명세서 갱신, 프롬프트 가이드 문서 작성 | `docs/TOUR-31-update-ai-spec` |

---

### 11.5 PR(Pull Request) 작성 표준 및 AI 코드 리뷰

모든 PR은 `develop` 브랜치를 타겟으로 생성하며, AI 리뷰 봇(CodeRabbit / Gemini Actions)이 정확한 컨텍스트를 파악할 수 있도록 아래 표준 템플릿을 준수합니다.

#### PR 작성 템플릿 규격
```markdown
## 🎫 이슈 번호
- Jira/Linear Ticket: #TOUR-12

## 🛠 작업 내용
- [ ] pgvector 날씨·계절 시맨틱 쿼리 빌더 구현
- [ ] 2단계 위경도 좌표 기반 최단 동선 정렬 알고리즘 추가
- [ ] LLM 프롬프트 토큰 최적화 및 JSON 응답 스키마 검증기 추가

## 📋 AI 리뷰어 집중 확인 요청 (Review Point)
- [ ] `search_candidate_places()`에서 비동기 DB 커넥션 누수 위험이 없는지 검토해줘.
- [ ] LLM 응답 실패 시 재시도 로직이 무한 루프에 빠질 가능성이 없는지 확인해줘.

## ✅ 자체 체크리스트 (Self-Check)
- [ ] pytest 단위 및 RAG 품질 평가 테스트 통과 여부
- [ ] 개인정보(PII) 및 API Key가 코드에 하드코딩되지 않았는지 확인
```

---

## 12. 환경변수 및 모델 주입 규격 (.env)

AI 서비스는 특정 모델이나 버전에 코드가 하드코딩되지 않도록, Pydantic `BaseSettings`를 통해 환경변수로부터 모델 및 접속 정보를 유연하게 주입받습니다.

### 12.1 설정 모델 (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Provider 설정 (ollama, gemini, openai 등)
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL_NAME: str = "llama3:8b" # 또는 qwen, gemini-1.5-flash 등
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    # Embedding Provider 설정
    EMBEDDING_PROVIDER: str = "openai" # openai 또는 local
    EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://tour_admin:tour_password@localhost:5432/tour_db"
    REDIS_URL: str = "redis://:tour_redis_pass@localhost:6379/0

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
```

### 12.2 `.env.example` 규격
```env
# LLM Engine Configuration
LLM_PROVIDER=ollama
LLM_MODEL_NAME=llama3:8b
OLLAMA_BASE_URL=http://localhost:11434
# GEMINI_API_KEY=your_gemini_key_if_used
# OPENAI_API_KEY=your_openai_key_if_used

# Embedding Model Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Database & Cache Connection
DATABASE_URL=postgresql+asyncpg://tour_admin:tour_password@localhost:5432/tour_db
REDIS_URL=redis://:tour_redis_pass@localhost:6379/0
```

---

> 💡 **연관 문서**: 
> - 공공데이터 수집 및 날씨 태그 사전 임베딩 적재: [BATCH.md](./BATCH.md)
> - 백엔드 API 컨트롤러 및 데이터베이스 스키마: [BACKEND.md](./BACKEND.md)
