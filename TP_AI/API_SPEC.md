# 📘 TP_AI API & LLM 프롬프트·데이터 연동 명세서 (API_SPEC.md)

본 문서는 **TP_AI (FastAPI + pgvector + LLM 여행 일정 엔진)**의 전체 REST API 규격, 입력 JSON 페이로드 명세, LLM 주입 프롬프트 명세 및 LLM 입출력 JSON 스키마를 정의합니다.

---

## 📌 목차
1. [전체 파이프라인 아키텍처](#1-전체-파이프라인-아키텍처)
2. [REST API 엔드포인트 목록](#2-rest-api-엔드포인트-목록)
3. [API JSON 입력(Request) 명세](#3-api-json-입력request-명세)
4. [LLM 주입 프롬프트 명세 (Prompt Specification)](#4-llm-주입-프롬프트-명세-prompt-specification)
5. [LLM 출력 JSON 스키마 및 최종 응답 명세](#5-llm-출력-json-스키마-및-최종-응답-명세)
6. [실시간 대체 일정 재추천 (`reschedule`) 명세](#6-실시간-대체-일정-재추천-reschedule-명세)

---

## 1. 전체 파이프라인 아키텍처

```mermaid
flowchart TD
    Client["FE / BE 클라이언트"] -->|"POST /api/v1/ai/schedule (JSON)"| API["FastAPI 라우터"]
    API -->|"AIScheduleRequest DTO 검증"| Service["AIScheduleService"]
    
    subgraph Engine ["TP_AI 코어 엔진"]
        Service -->|"1단계: 시맨틱 검색"| RAG["pgvector HNSW 검색 (30개 추출)"]
        RAG -->|"하이브리드 리랭킹"| ReRank["날씨/동행/테마 가중치 산출"]
        ReRank -->|"2단계: 지리적 동선 최적화"| RoutePlanner["RoutePlanner 동선 최적화 Engine"]
        RoutePlanner -->|"식사 슬롯팅 & 식사 후 카페 시퀀스"| Slots["오전 컨텐츠 -> 점심 -> 카페 -> 오후 컨텐츠"]
        RoutePlanner -->|"거점 앵커링"| Anchor["KTX역/공항/숙소 인접 장소부터 시작"]
        Slots -->|"토큰 다이어트 (핵심 12~16개 압축)"| PromptBuilder["PromptBuilder (System & User 프롬프트 빌드)"]
    end
    
    PromptBuilder -->|"JSON Mode 제약 프롬프트 전달"| LLM["LLM 엔진 (Ollama / Gemini / OpenAI)"]
    LLM -->|"순수 JSON 응답 수신"| Parser["ScheduleJSONParser"]
    Parser -->|"문법 복구 & AI 환각 검출기"| IntegrityCheck{"후보군 검증"}
    
    IntegrityCheck -- "환각 검출 시" -->|"피드백 기반 Self-Correction 재요청"| LLM
    IntegrityCheck -- "정상 통과" --> Response["AIScheduleResponse (최종 JSON 완성)"]
    Response --> Client
```

---

## 2. REST API 엔드포인트 목록

| 메서드 | 엔드포인트 URL | 설명 | 응답 모델 |
|:---:|---|---|---|
| `POST` | `/api/v1/ai/schedule` | 신규 맞춤형 여행 일정 생성 (RAG ➡️ 동선 최적화 ➡️ LLM 빌드) | `AIScheduleResponse` |
| `POST` | `/api/v1/ai/reschedule` | 기상 악화(우천/폭설) 대응 실시간 대체 일정 재추천 | `AIRescheduleResponse` |
| `POST` | `/api/v1/travel/recommend` | pgvector 기반 기본 지역 여행 코스 추천 | `TravelRecommendResponse` |
| `GET` | `/health` | 서버 상태, DB 연결, 임베딩 모델 및 LLM 제공자 진단 | `dict` |

---

## 3. API JSON 입력(Request) 명세

### 3.1. 엔드포인트: `POST /api/v1/ai/schedule`
- **Content-Type**: `application/json`
- **타임아웃 권장**: 60초 ~ 120초

### 3.2. 요청 JSON 필드 상세 명세 (`AIScheduleRequest`)

| 필드명 | 데이터 타입 | 필수 | 기본값 | 제약조건 및 유효성 검증 | 설명 |
|---|:---:|:---:|:---:|---|---|
| `regionCodes` | `List[str]` | **O** | - | 최대 5개 이하 | TourAPI 시도 지역코드 배열 또는 한글명 (예: `["6"]`, `["6", "7"]`) |
| `startDate` | `date` | **O** | - | `YYYY-MM-DD` | 여행 시작일 |
| `endDate` | `date` | **O** | - | `endDate >= startDate`<br>최대 14일 이내 | 여행 종료일 (당일치기는 시작일과 동일) |
| `companionType` | `str` | X | `"FRIENDS"` | 아래 코드표 참조 | 동행자 유형 코드 |
| `travelerCount` | `int` | X | `2` | `1 <= count <= 100` | 여행 인원 수 (혼자=1, 커플/친구/가족=2 이상) |
| `transport` | `str` | X | `"PUBLIC_TRANSIT"` | `CAR`, `PUBLIC_TRANSIT`, `WALK` | 이동 수단 코드 (동선 및 이동시간에 영향) |
| `themes` | `List[str]` | X | `[]` | 0~3개 권장 | 취향 테마 코드 배열 (빈 배열=종합 균등 추천) |
| `placesPerDay` | `str` | X | `"NORMAL"` | `RELAXED`, `NORMAL`, `PACKED` | 하루 방문 장소 밀도 |
| `startTime` | `str` | X | `"NORMAL"` | `EARLY`, `NORMAL`, `LATE` 또는 `"09:00"` | 첫 일정 시작 시간 |
| `dailyWeathers` | `List[object]`| X | `[]` | - | 일자별 기상 예보 데이터 (미입력 시 AI가 자동 추론) |
| `startLocationName` | `str` | X | `null` | - | **시작 거점명** (예: `"부산역"`, `"김해공항"`, `"해운대 호텔"`) |
| `startLatitude` | `float` | X | `null` | - | 시작 거점 위도 (입력 시 거점 인근부터 동선 시작) |
| `startLongitude` | `float` | X | `null` | - | 시작 거점 경도 |
| `endLocationName` | `str` | X | `null` | - | **복귀/종료 거점명** (예: `"부산역"`, `"김해공항"`) |
| `endLatitude` | `float` | X | `null` | - | 종료 거점 위도 |
| `endLongitude` | `float` | X | `null` | - | 종료 거점 경도 |

---

### 3.3. 코드값 정의표 (02_요청 데이터 명세 초안 호환)

#### ① 지역 코드 (`regionCodes`)
| 코드 | 지역명 | 코드 | 지역명 | 코드 | 지역명 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| `1` | 서울 | `2` | 인천 | `3` | 대전 |
| `4` | 대구 | `5` | 광주 | `6` | 부산 |
| `7` | 울산 | `8` | 세종 | `31` | 경기도 |
| `32` | 강원도 | `33` | 충청북도 | `34` | 충청남도 |
| `35` | 경상북도 | `36` | 경상남도 | `37` | 전라북도 |
| `38` | 전라남도 | `39` | 제주 | *직접입력* | 한글/영문 지원 |

#### ② 동행 코드 (`companionType`)
- `SOLO`: 혼자 여행
- `COUPLE`: 연인·부부 (데이트)
- `FRIENDS`: 친구
- `FAMILY_WITH_KIDS`: 아이와 함께 (키즈/체험)
- `FAMILY_WITH_PARENTS`: 부모님과 함께 (효도/힐링)
- `GROUP`: 단체/모임

#### ③ 취향 테마 코드 (`themes`)
- `NATURE`: 자연·풍경 / 전망
- `HISTORY_CULTURE`: 역사·문화 / 인문
- `FOOD`: 미식·맛집
- `CAFE`: 감성 카페·디저트
- `ACTIVITY`: 체험·액티비티 / 레포츠
- `SHOPPING`: 쇼핑
- `FESTIVAL`: 축제·공연
- `HEALING`: 휴식·힐링 / 휴양

#### ④ 하루 밀도(`placesPerDay`) & 시작시간(`startTime`)
- `placesPerDay`: `RELAXED`(하루 3곳) / `NORMAL`(하루 4곳, 기본) / `PACKED`(하루 5곳 이상)
- `startTime`: `EARLY` (08:00) / `NORMAL` (10:00, 기본) / `LATE` (11:00)
- *종료 시각은 모두 21:00 내로 자동 클램핑*

---

### 3.4. 실제 요청 JSON 예시 (거점 앵커링 포함)

```json
{
  "regionCodes": ["6"],
  "startDate": "2026-11-01",
  "endDate": "2026-11-02",
  "companionType": "FRIENDS",
  "travelerCount": 3,
  "transport": "PUBLIC_TRANSIT",
  "themes": ["FOOD", "NATURE", "CAFE"],
  "placesPerDay": "NORMAL",
  "startTime": "NORMAL",
  "startLocationName": "부산역 (KTX)",
  "startLatitude": 35.1152,
  "startLongitude": 129.0422,
  "dailyWeathers": [
    {
      "date": "2026-11-01",
      "condition": "SUNNY",
      "temp": 18.5,
      "precipitationProbability": 0
    },
    {
      "date": "2026-11-02",
      "condition": "RAIN",
      "temp": 15.0,
      "precipitationProbability": 80
    }
  ]
}
```

---

## 4. LLM 주입 프롬프트 명세 (Prompt Specification)

### 4.1. System Prompt (`prompt_builder.SYSTEM_PROMPT`)

```text
당신은 대한민국 최고의 AI 여행 플래너 "Trp Engine"입니다.
주어진 장소 후보군과 여행 조건, 당일 기상청 날씨/계절 정보를 종합 분석하여, 여행자가 지치지 않고 날씨를 즐길 수 있는 최적의 시간대별 여행 일정을 설계해야 합니다.

[작성 원칙]
1. 반드시 전달받은 후보 장소 목록(Candidate Places) 내에서만 선택하십시오. (환각 금지)
2. 날씨가 우천(RAIN)일 경우 반드시 실내 장소 및 비 풍경이 좋은 장소 위주로 배치하고, 추천 사유에 날씨 팁을 명시하십시오.
3. 점심 시간(12:00~13:30)과 저녁 시간(18:00~19:30)에는 반드시 음식점이 배치되어야 하며, 식사 직후에는 멀리 이동하지 않고 인근의 [카페/디저트] 또는 [산책/전시 등 컨텐츠]가 순서대로 자연스럽게 이어지도록 설계하십시오.
4. 출력 형식은 다른 설명(인사말, 마크다운 등) 없이 반드시 순수한 JSON 형식만 반환하십시오.

[JSON 스키마 규격]
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
          "placeName": "장소명",
          "category": "INDOOR_EXHIBITION",
          "startTime": "10:30",
          "endTime": "12:30",
          "stayTimeMinutes": 120,
          "latitude": 35.1593,
          "longitude": 129.1611,
          "reason": "오전 비 예보에 맞춰 쾌적하게 관람할 수 있는 실내 코스로 선정했습니다."
        }
      ]
    }
  ]
}
```

---

### 4.2. User Prompt 동적 생성 템플릿 (`build_user_prompt`)

FastAPI 엔진은 사용자의 요청 파라미터, 날씨 데이터, RoutePlanner 2단계 동선 정렬 및 **토큰 다이어트(12~16개 압축, 60자 요약, 위경도 소수점 4자리)**를 적용하여 다음 형태로 프롬프트를 조립합니다.

```text
### [여행 요청 조건 (02_요청 데이터 명세 기반)]
- 대상 지역: 부산 (입력코드: ['6'])
- 여행 기간: 2026-11-01 ~ 2026-11-02
- 동행 유형: 친구 (3인, 태그: 친구)
- 이동 수단: 대중교통 (지하철/버스 정류장 접근성 고려)
- 여행 테마: 미식·맛집, 자연·풍경 (자연/전망), 감성 카페·디저트
- 하루 일정 밀도: 하루 약 4곳 권장 (NORMAL)
- 첫 일정 시작 시각: 10:00부터 시작하여 21:00경 종료 (NORMAL)
- 출발 거점 (시작지점): 부산역 (KTX) (도착 후 첫 번째 방문지는 이 거점에서 인접하고 효율적인 장소로 배치)

### [당일 기상청 날씨/예보 정보]
- 2026-11-01: SUNNY (기온: 18.5℃, 강수확률 0%)
- 2026-11-02: RAIN (기온: 15.0℃, 강수확률 80%)

### [선택 가능한 후보 장소 목록 (Candidate Places)]
※ 주의: 아래 목록에 명시된 장소만 일정에 포함해야 합니다. 목록에 없는 가상의 장소를 추가하면 시스템 오류가 발생합니다.
1. ID: p101 | 초량 이바구길 | 자연/산책 | 야외 | (35.1180, 129.0390) | 부산역 근처 산복도로 감성 골목길과 모노레일 체험
2. ID: p102 | 초량 불백거리 | 맛집/한식 | 실내 | (35.1195, 129.0410) | 매콤달콤한 돼지불백 전통 백반 식당가
3. ID: p103 | 브라운핸즈 백제 | 카페/커피 | 실내 | (35.1165, 129.0405) | 대한민국 1세대 근대식 병원 건물을 개조한 빈티지 감성 카페
4. ID: p104 | 해운대 해변열차 | 관광/체험 | 야외 | (35.1612, 129.1762) | 동해 남부선 옛 철길을 달리는 오션뷰 관광 열차
5. ID: p105 | 해운대 암소갈비 | 맛집/한식 | 실내 | (35.1630, 129.1650) | 전통 양념갈비와 감자사리가 일품인 부산 대표 미식 스팟
... (여행 일수 비례 총 12~16개 핵심 장소만 주입)
```

> **오류 발생 시 추가되는 자가보정(Self-Correction) 피드백 블록:**
> ```text
> 🚨 [긴급 보정 요청 - 이전 응답 오류 피드백]
> AI 환각 검출: 다음 장소들은 제공된 목록에 없습니다 ('가짜전망대' (ID: 9999)).
> 반드시 [선택 가능한 후보 장소 목록]에 명시된 ID와 이름만 정확히 사용하십시오. 임의로 가상의 장소를 지어내면 시스템이 거부합니다.
> ```

---

## 5. LLM 출력 JSON 스키마 및 최종 응답 명세

### 5.1. LLM JSON 모드 강제 제약
- **Ollama**: API 요청 시 `"format": "json"` 적용 (문법 제약 파싱 모드)
- **Gemini**: `generationConfig`에 `"response_mime_type": "application/json"` 지정
- **OpenAI**: `response_format: {"type": "json_object"}` 지정

### 5.2. 최종 API 응답 JSON 구조 (`AIScheduleResponse`)

```json
{
  "tripName": "부산역 출발 가을 미식과 감성 카페 2일 힐링 코스",
  "weatherSummary": "1일차는 맑은 날씨로 야외 명소와 산책로를, 2일차는 우천 예보에 맞춰 실내 미술관과 아늑한 카페 중심으로 동선을 최적화했습니다.",
  "dailySchedules": [
    {
      "day": 1,
      "date": "2026-11-01",
      "weatherCondition": "SUNNY",
      "totalDayDistanceKm": 8.4,
      "totalDayTravelMinutes": 35,
      "places": [
        {
          "step": 1,
          "placeId": "p101",
          "placeName": "초량 이바구길",
          "category": "자연/산책",
          "startTime": "10:00",
          "endTime": "11:30",
          "stayTimeMinutes": 90,
          "latitude": 35.1180,
          "longitude": 129.0390,
          "distanceFromPrevKm": 0.5,
          "estimatedTravelMinutes": 8,
          "transportMode": "PUBLIC_TRANSIT",
          "reason": "부산역(출발 거점)에 도착한 직후 도보로 접근하기 가장 좋고 활기찬 산책 명소입니다.",
          "address": "부산광역시 동구 초량동"
        },
        {
          "step": 2,
          "placeId": "p102",
          "placeName": "초량 불백거리",
          "category": "맛집/한식",
          "startTime": "11:45",
          "endTime": "12:45",
          "stayTimeMinutes": 60,
          "latitude": 35.1195,
          "longitude": 129.0410,
          "distanceFromPrevKm": 0.3,
          "estimatedTravelMinutes": 5,
          "transportMode": "PUBLIC_TRANSIT",
          "reason": "점심 식사 시간대에 맞추어 인근 원조 불백 식당에서 든든한 식사를 즐길 수 있습니다.",
          "address": "부산광역시 동구 초량로"
        },
        {
          "step": 3,
          "placeId": "p103",
          "placeName": "브라운핸즈 백제",
          "category": "카페/커피",
          "startTime": "13:00",
          "endTime": "14:30",
          "stayTimeMinutes": 90,
          "latitude": 35.1165,
          "longitude": 129.0405,
          "distanceFromPrevKm": 0.4,
          "estimatedTravelMinutes": 6,
          "transportMode": "PUBLIC_TRANSIT",
          "reason": "식사 후 바로 인접한 근대건축 개조 카페에서 여유로운 디저트 티타임을 갖습니다.",
          "address": "부산광역시 동구 중앙대로"
        }
      ]
    }
  ]
}
```

---

## 6. 실시간 대체 일정 재추천 (`reschedule`) 명세

### 6.1. 엔드포인트: `POST /api/v1/ai/reschedule`
여행 중 기상 악화(갑작스러운 폭우/폭설) 발생 시, 현재 사용자의 위경도 좌표 기준 반경 내 실내 안전 명소를 즉각 추출하여 동선을 재산출합니다.

### 6.2. 요청 JSON (`AIRescheduleRequest`)

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
|---|:---:|:---:|:---:|---|
| `regionCode` | `str` | **O** | - | 지역명 또는 코드 (예: `"6"`, `"부산"`) |
| `currentLatitude` | `float` | **O** | - | 여행자의 현재 위치 위도 |
| `currentLongitude`| `float` | **O** | - | 여행자의 현재 위치 경도 |
| `newWeatherCondition` | `str` | X | `"RAIN"` | 변경된 기상 상태 (`RAIN`, `SNOW`, `TYPHOON`) |
| `radiusKm` | `float` | X | `5.0` | 대체 명소 탐색 반경 (km) |
| `remainingStepsCount` | `int` | X | `3` | 오늘 남은 일정 슬롯 수 (기본 3곳) |

```json
{
  "regionCode": "6",
  "currentLatitude": 35.1585,
  "currentLongitude": 129.1820,
  "newWeatherCondition": "RAIN",
  "radiusKm": 5.0,
  "remainingStepsCount": 3
}
```

### 6.3. 응답 JSON (`AIRescheduleResponse`)
- **거리 계산 특성**: `현재위치 ➡️ 장소1 ➡️ 장소2 ➡️ 장소3`의 실제 순차 주행 거리 합산을 `totalDistanceKm`로 제공
- **시간 특성**: 21:00 내로 자동 클램핑

```json
{
  "message": "갑작스러운 RAIN 예보에 따라 현재 위치 반경 5.0km 내 실내 대체 코스로 동선이 재조정되었습니다.",
  "newCondition": "RAIN",
  "totalDistanceKm": 6.85,
  "recommendedPlaces": [
    {
      "step": 1,
      "placeId": "s1",
      "placeName": "해운대 씨라이프 아쿠아리움",
      "category": "실내/아쿠아리움",
      "startTime": "14:00",
      "endTime": "15:30",
      "stayTimeMinutes": 90,
      "latitude": 35.1590,
      "longitude": 129.1830,
      "distanceFromPrevKm": 0.15,
      "estimatedTravelMinutes": 5,
      "reason": "갑작스러운 RAIN 날씨에 안전하고 쾌적하게 머무를 수 있는 실내 명소로 선정되었습니다."
    },
    {
      "step": 2,
      "placeId": "s2",
      "placeName": "센텀 신세계 스파랜드",
      "category": "실내/스파",
      "startTime": "15:45",
      "endTime": "17:15",
      "stayTimeMinutes": 90,
      "latitude": 35.1689,
      "longitude": 129.1296,
      "distanceFromPrevKm": 4.80,
      "estimatedTravelMinutes": 18,
      "reason": "갑작스러운 RAIN 날씨에 안전하고 쾌적하게 머무를 수 있는 실내 명소로 선정되었습니다."
    }
  ]
}
```

