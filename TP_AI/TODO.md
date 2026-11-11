# 📋 TP_AI 개발 및 고도화 백로그 (TODO.md)

## 🛡️ 1. 보안 하드닝 (Security Hardening) - 100% 완료

- [x] **CWE-400 (자원 고갈 및 DoS 방어 - 입력 상한 검증)**:
  - 여행 기간 상한 검증 (`travel_days <= 14일`) 추가로 무한 일정 생성 요청 방어
  - 연계 가능 지역 수 제한 (`regionCodes <= 5개`) 추가
  - 인원 수 상한 제한 (`travelerCount <= 100명`) 추가
- [x] **CWE-209 (민감 내부 시스템 정보 노출 방지)**:
  - `endpoints/ai.py` 및 `endpoints/travel.py`의 `HTTPException(500, detail=...)` 개선 완료
  - `settings.DEBUG == False` 시 내부 상세 에러 은폐 및 표준 안내 메시지 반환, 스택트레이스는 서버 로그(`app_logger.exception`)에만 안전하게 기록
- [x] **CWE-770 (HTTP Client 커넥션 누수 방지 및 풀링)**:
  - `app/core/llm_client.py`에서 매 호출마다 `httpx.AsyncClient`를 생성/폐기하던 구조를 영속 커넥션 풀(`max_keepalive_connections=20`)로 전환
  - `main.py`의 lifespan 종료 시 `await llm_client.close()` 수명주기 관리 적용
- [x] **CWE-532 (API Key 유출 방지)**:
  - Gemini 호출 시 URL Query 파라미터 대신 `x-goog-api-key` 헤더 인증 사용
- [x] **CORS 설정 프로덕션 경고**:
  - `APP_ENV == "production"` 상태에서 `CORS_ORIGINS`에 와일드카드(`*`)가 포함된 경우 보안 경고 로그 발생 적용

---

## ⚙️ 2. 비즈니스 로직 및 시스템 결함 보완 (Defects & Logic Fixes) - 100% 완료

- [x] **AI 환각 검출기(`verify_candidates_integrity`) 엄격화**:
  - "카페", "식당", "공원" 등 일반 명사 악용 및 1~2글자 느슨한 부분 일치 허점 차단
  - 3글자 이상 및 상호 길이 비율 50% 이상일 때만 유사 인정
- [x] **실시간 대체 일정(`reschedule`) 누적 이동 거리 왜곡 결함 수정**:
  - 기존 `(현재위치->스팟A) + (현재위치->스팟B)` 단순 합산에서 `현재위치 ➡️ 장소1 ➡️ 장소2 ➡️ 장소3` 실제 순차 주행 시퀀스 누적 거리(`totalDistanceKm`)로 교정 완료
  - 각 스팟별 구간 이동거리(`distanceFromPrevKm`) 및 이동시간(`estimatedTravelMinutes`) 정상 바인딩
- [x] **일정 시각 24시 오버플로우 방지 및 시간대 정규화**:
  - `reschedule()` 및 `build_fallback_schedule()`에서 명세서 규격(종료는 모두 21:00)에 맞추어 21:00 이전으로 클램핑 및 두 자릿수 포맷(`f"{h:02d}:00"`) 정규화 완료
- [x] **FastAPI 이벤트 루프 블로킹 해소 (PyTorch CPU 연산 격리)**:
  - `SentenceTransformer.encode()` 연산을 `await asyncio.to_thread()` 비동기 워커 스레드 풀로 위임하여 다중 요청 처리 지연 차단
- [x] **대량 스팟 등록 시 N+1 `refresh()` 비동기 DB I/O 병목 제거**:
  - `travel_service.create_bulk_spots()` 루프 내 `await db.refresh(s)` 제거로 벌크 성능 극대화
- [x] **임베딩 모듈 동시성 락 및 로거 통일**:
  - `app/core/embedding.py`의 모델 로드 레이스 컨디션 방지(`threading.Lock()`) 및 `app_logger` 통일
- [x] **Haversine 부동소수점 도메인 에러 방어**:
  - 삼각함수 정밀도 오차(`a > 1.0`)로 인한 `math domain error` 방어 클램핑 적용

---

## 🚀 3. 핵심 엔진 및 고도화 완료 기능 (Core Engine Done)

- [x] **기상청 예보 DB(`weather_forecasts`) 1순위 조회 및 계절 Fallback 연동**:
  - `WeatherForecast` 모델 신설 및 `weather_service.get_daily_weathers()` 구현
  - 일정 생성 시 클라이언트가 날씨를 미입력하더라도 DB에 적재된 기상청 예보 데이터를 1순위로 조회하여 일정에 자동 반영 (DB 미적재 시 계절 Fallback 보완)
- [x] **출발지/숙소 거점 앵커링 (Anchor Routing)**:
  - KTX역, 공항, 숙소 등 시작 거점(`startLatitude`, `startLongitude`, `startLocationName`) 및 복귀 거점 지정 지원
  - Day 1 시작 시 거점과의 거리 감쇠 가중치(Distance Weighting)를 적용하여 거점 인근 명소부터 일정 시작
  - LLM 프롬프트에 거점 지침 주입으로 자연스러운 추천 사유 생성 유도
- [x] **프롬프트 토큰 다이어트 및 추론 Latency 단축**:
  - 여행 일수 대비 필요 장소 수 + 예비 4곳 압축 (30개 ➡️ 12~16개)
  - 장소 설명문 60자 요약 및 위경도 소수점 4자리 정규화로 프롬프트 토큰 40% 이상 절감
- [x] **식사 시간대 및 인접 카페/컨텐츠 시퀀스 최적화**:
  - 점심(12:00~13:30) 및 저녁(18:00~19:30) 식당 강제 슬롯팅
  - [식사 ➡️ 인접 카페 or 컨텐츠] 거리 감쇠 가중치($0.6^2$) 적용
- [x] **복수 지역코드 연계 분기 파이프라인**:
  - `regionCodes`가 2개 이상일 때 기존 단일 지역 로직을 보존하면서 `_generate_multi_region_schedule`로 안전 분기
- [x] **LLM 제어 및 자가보정 재요청 (Self-Correction Retry)**:
  - 마크다운 정제 및 JSON 끝 쉼표 자동 복구 (`repair_json_syntax`)
  - 환각/포맷 에러 발생 시 피드백 기반 자동 재요청(지수 백오프) 및 100% 안전한 Fallback 보장
- [x] **기상 악화 대응 실시간 대체 일정 재추천 (`POST /api/v1/ai/reschedule`)**:
  - 사용자 현재 위치 기준 반경 내 실내 안전 명소 추출 및 동선 재조정

---

## 📌 4. 향후 확장 과제 (Future Backlog)

- [ ] **실제 DB 연동 시 기상청 예보(`weather_forecasts`) 테이블 실제 스키마 생성 및 배치 적재 체크**:
  - `init_db()` 실행 시 `weather_forecasts` DDL 정상 반영 확인
  - 기상청 단기/중기 예보 배치 파이프라인에서 적재된 일자별 예보 데이터와 AI 스케줄러의 실제 연동 상태 E2E 체크
- [ ] **외부 경로/모빌리티 API 연동 검토**:
  - 카카오 모빌리티 API 또는 OSRM(Open Source Routing Machine) 연동을 통한 실제 도로 주행 기준 시간 산출
- [ ] **PostgreSQL pgvector 로컬 Docker E2E 시딩 검증**:
  - `docker compose up -d` 기동 후 `scripts/seed_travel_data.py` 실행 및 실제 HNSW 인덱스 벡터 검색 E2E 테스트
- [-] **카카오맵 뷰포트 바인딩**:
  - 사용자 요청에 따라 현재 범위에서 제외 (Out of Scope)
