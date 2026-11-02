# TP

AI와 공공데이터(한국관광공사 TourAPI, 기상청 예보)를 바탕으로 여행 일정과 최적 동선을 추천하는 플랫폼입니다.

전체 아키텍처, 서비스 흐름, 기술 스택, 협업 규칙은 [ROOT.md](./ROOT.md)에 정리되어 있습니다.
서비스들이 함께 쓰는 DB 테이블 구조는 [DATABASE.md](./DATABASE.md)(초안)에 있습니다.

## 저장소 구성

| 폴더 | 역할 | 기술 | 명세 문서 | 현재 상태 |
| :--- | :--- | :--- | :--- | :--- |
| [TP_AI](./TP_AI) | RAG 장소 추천, 동선 최적화 | Python, FastAPI, pgvector | [AI.md](./TP_AI/AI.md) | 코드 있음 ([README](./TP_AI/README.md)) |
| [TP_BATCH](./TP_BATCH) | TourAPI 수집·정제, 임베딩 적재 | Python, PostgreSQL, APScheduler | [BATCH.md](./TP_BATCH/BATCH.md) | 코드 있음 ([README](./TP_BATCH/README.md)) |
| [TP_BE](./TP_BE) | 여행 REST API, AI 서비스 연동 | Kotlin, Spring Boot | [BACKEND.md](./TP_BE/BACKEND.md) | 명세만 있음 |
| [TP_FE](./TP_FE) | 카카오맵 기반 일정·동선 화면 | React, TypeScript, Vite | [FRONTEND.md](./TP_FE/FRONTEND.md) | 명세만 있음 |

각 서비스의 설치·실행 방법은 해당 폴더의 README를 참고하세요.

## 비밀값 관리

API 키와 DB 비밀번호는 저장소에 올리지 않습니다. 루트 [.gitignore](./.gitignore)가 아래 파일을 막고 있습니다.

- `.env` — 각 폴더의 `.env.example`을 복사해서 만듭니다.
- `secrets*.properties` — TP_BATCH는 `secrets-api.properties.example`을 복사해서 TourAPI·기상청 키를 넣습니다.
- 개인키·인증서(`*.pem`, `*.key` 등), 로그, 수집 데이터 백업(`TP_BATCH/output/`)

커밋 전에 `git status`로 위 파일이 목록에 없는지 확인하세요.

## 협업 규칙

브랜치는 `main`(배포) / `develop`(통합) / `feat/`·`fix/`·`refactor/`·`docs/`(작업)으로 나누고, 이름은 `접두사/티켓번호-작업내용` 형식을 씁니다. 모든 PR은 `develop`을 대상으로 합니다. 자세한 내용은 [ROOT.md](./ROOT.md)의 'Git 브랜치 전략 및 협업 규칙'을 보세요.
