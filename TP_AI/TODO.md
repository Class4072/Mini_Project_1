# 📋 TP_AI 개발 및 고도화 백로그 (TODO.md)

## 🛡️ 1. 보안 취약점 점검 및 보완 계획 (Security Hardening)

- [x] **CWE-400 (자원 고갈 및 DoS 방어 - 입력 상한 검증)**:
  - 여행 기간 상한 검증 (`travel_days <= 14일`) 추가로 무한 일정 생성 요청 방어
  - 연계 가능 지역 수 제한 (`regionCodes <= 5개`) 추가
  - 인원 수 상한 제한 (`travelerCount <= 100명`) 추가
- [x] **CWE-209 (민감 내부 시스템 정보 노출 방지)**:
  - `endpoints/ai.py` 및 `endpoints/travel.py`의 `HTTPException(500, detail=...)` 개선 완료
  - `settings.DEBUG == False` 시 내부 상세 에러 은폐 및 표준 안내 메시지 반환, 스택트레이스는 서버 로그(`app_logger.exception`)에만 안전하게 기록
- [ ] **CWE-770 (HTTP Client 커넥션 누수 방지 및 풀링)**:
  - `app/core/llm_client.py`에서 매 호출마다 `httpx.AsyncClient`를 생성/폐기하는 구조 개선
  - 커넥션 풀(`max_keepalive_connections=20`) 및 수명주기 관리(`lifespan shutdown`) 적용
- [ ] **CORS 설정 프로덕션 경고**:
  - `APP_ENV == "production"` 상태에서 `CORS_ORIGINS`에 와일드카드(`*`)가 포함된 경우 보안 경고 로그 발생

---

## ⚙️ 2. 비즈니스 로직 및 시스템 결함 보완 계획 (Defects & Logic Fixes)

- [x] **AI 환각 검출기(`verify_candidates_integrity`) 엄격화**:
  - "카페", "식당", "공원" 등 일반 명사 악용 및 1~2글자 느슨한 부분 일치 허점 차단
  - 3글자 이상 및 상호 길이 비율 50% 이상일 때만 유사 인정
- [x] **실시간 대체 일정(`reschedule`) 누적 이동 거리 왜곡 결함 수정**:
  - 기존 `(현재위치->스팟A) + (현재위치->스팟B)` 단순 합산에서 `현재위치 ➡️ 스팟1 ➡️ 장소2 ➡️ 장소3` 실제 순차 주행 시퀀스 누적 거리(`totalDistanceKm`)로 교정 완료
  - 각 스팟별 구간 이동거리(`distanceFromPrevKm`) 및 이동시간(`estimatedTravelMinutes`) 정상 바인딩
- [x] **일정 시각 24시 오버플로우 방지 및 시간대 정규화**:
  - `reschedule()` 및 `build_fallback_schedule()`에서 명세서 규격(종료는 모두 21:00)에 맞추어 21:00 이전으로 클램핑 및 두 자릿수 포맷(`f"{h:02d}:00"`) 정규화 완료
- [ ] **FastAPI 이벤트 루프 블로킹 해소 (PyTorch CPU 연산 격리)**:
  - `SentenceTransformer.encode()` 연산을 `await asyncio.to_thread()`로 감싸 비동기 워커 스레드 풀에서 실행
- [ ] **대량 스팟 등록 시 N+1 `refresh()` 비동기 DB I/O 병목 제거**:
  - `travel_service.create_bulk_spots()` 루프 내 `await db.refresh(s)` 제거로 벌크 성능 극대화
- [ ] **임베딩 모듈 동시성 락 및 로거 통일**:
  - `app/core/embedding.py`의 모델 로드 레이스 컨디션 방지(`threading.Lock()`) 및 `app_logger` 통일

---

## 📌 3. 프롬프트 및 성능 최적화 (Next Sprints)

### 1. 프롬프트 토큰 다이어트 및 추론 속도 최적화 방법
- **목적**: 불필요한 프롬프트 토큰을 줄여 LLM 추론 지연시간(Latency)을 40% 이상 단축하고 토큰 비용 절감
- **구체적인 구현 전략**:
  1. **후보 장소 개수 압축 (30개 ➡️ 12~16개)**:
     - RAG 1단계에서는 광범위한 탐색을 위해 30개를 추출하되, 2단계 지리적 동선 최적화(RoutePlanner)를 거친 후에는 여행 일수(예: 2박 3일이면 하루 4곳 기준 12곳 + 예비 4곳 = 총 16곳)에 맞춘 핵심 후보군만 LLM 프롬프트에 전달.
  2. **장소 설명문 텍스트 압축**:
     - 원문 `description` 전문 대신 핵심 설명문(50~80자 내외) 및 대표 태그 2~3개만 프롬프트에 주입.
  3. **내부 메타데이터 제거**:
     - 위도, 경도 좌표의 소수점 자릿수 정리(소수점 4자리까지), 시스템 내부 플래그 등 LLM의 시간표/사유 작성에 불필요한 원시 데이터 제거.

### 2. 외부 경로/모빌리티 API 연동 검토
- [ ] 카카오 모빌리티 API 또는 OSRM(Open Source Routing Machine) 연동을 통한 실제 도로 주행 기준 시간 산출
- [ ] 출발지/도착지 앵커링 (숙소, KTX 역, 공항 등 시작 지점과 복귀 지점을 포함한 루프형 이동 시간표 계산)

---

## ✅ 4. 완료된 작업 (Done)

- [x] RAG 기반 날씨·계절 시맨틱 장소 추출 (pgvector HNSW 코사인 유사도)
- [x] Haversine 거리 계산 및 지그재그 이동 방지 Nearest Neighbor 정렬
- [x] `02_요청 데이터 명세 초안` JSON 파싱 및 TourAPI 지역코드/동행/테마 매핑 (`CodeMapper`)
- [x] 식사 시간대 식당 배치 및 [식사 ➡️ 인접 카페 or 컨텐츠] 시퀀스 & 동선 거리 감쇠 가중치 적용
- [x] 복수 지역코드(`regionCodes: ["6", "7"]`) 분기 파이프라인 (`_generate_multi_region_schedule`)
- [x] LLM 응답 정제(마크다운 제거), Pydantic v2 스키마 구조화
- [x] AI 환각(후보군 외 가짜 장소 날조) 검출기 및 Self-Correction 재요청/Fallback 보장
- [x] 기상 악화 실시간 대체 일정 재추천 (`POST /api/v1/ai/reschedule`)
- [x] Gemini API Key 헤더 인증 전환(CWE-532 방지) 및 Haversine 부동소수점 도메인 에러 방어
- [x] DB 커넥션 풀 튜닝 (`pool_size=10, max_overflow=20, pool_recycle=1800`)
