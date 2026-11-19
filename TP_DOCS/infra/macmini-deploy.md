# 맥미니 개발 서버 배포

TP의 4개 서비스(FE·BE·AI·배치)를 맥미니에서 도커로 실행하는 방법입니다.
공개 주소: https://tp.ricebug.dev (연결 방법은 [cloudflare-tunnel.md](./cloudflare-tunnel.md))

## 구성

```
인터넷 ─ Cloudflare ─ 터널(cloudflared) ─ 127.0.0.1:80  fe (nginx)
                                                         └ /api → be:8080 ─ ai:8000
                                                                    └ redis (compose 내부 전용)
맥미니 호스트: PostgreSQL(pgvector 컨테이너, 5432) · Ollama(11434)
  → 컨테이너에서는 host.docker.internal 로 접근
batch: 상주 스케줄러, 매일 04:00 TourAPI 수집 (aidb)
```

| 서비스 | 이미지 | 호스트 포트 | 비고 |
| :--- | :--- | :--- | :--- |
| fe | `tp-fe` | `127.0.0.1:80` | node 빌드 → nginx. `/api` 를 be 로 프록시 |
| be | `tp-be` | `127.0.0.1:8080` | Spring Boot. DB `tour_db`, Flyway(`tp_owner`) |
| ai | `tp-ai` | `127.0.0.1:8000` | FastAPI + CPU torch. DB `aidb` |
| batch | `tp-batch` | 없음 | `python -m app.cli schedule` |
| redis | `redis:7-alpine` | 없음 | BE 캐시용, 디스크 저장 안 함 |

포트는 모두 `127.0.0.1` 에만 열려 있어 LAN·외부에서 직접 접속할 수 없습니다. 외부 접속은 터널로만 합니다.

## 사전 준비 (처음 한 번)

1. Docker: 맥미니는 colima 사용. **`brew install docker-buildx` 필요** (없으면 Dockerfile 의 `RUN --mount` 에서 빌드 실패)
2. 저장소: 내장 디스크(APFS)에 clone. 외장 SSD(ExFAT)는 `._*` 파일이 생겨 git·Gradle 이 깨지므로 쓰지 않음
3. `.env` 4개 준비 (값은 저장소에 올리지 않음)

| 파일 | 필요한 키 |
| :--- | :--- |
| 루트 `.env` | `AI_DATABASE_URL`(필수, aidb 접속 URL), `VITE_KAKAO_MAP_API_KEY`, `FE_PORT`·`BE_PORT`·`AI_PORT`, `TAG` |
| `TP_BE/.env` | `DB_USER`·`DB_PASSWORD`(tp_backend), `FLYWAY_USER`·`FLYWAY_PASSWORD`(tp_owner), `FLYWAY_ENABLED`, `CACHE_TYPE`, `AI_SERVICE_TIMEOUT_SECONDS`, `SHARE_BASE_URL`, `KAKAO_MOBILITY_REST_API_KEY`(선택) |
| `TP_AI/.env` | `.env.example` 그대로 (DB 주소는 루트 `AI_DATABASE_URL` 이 덮어씀) |
| `TP_BATCH/.env` | `DB_NAME`·`DB_USER`·`DB_PASSWORD`(aidb), `TOUR_API_SERVICE_KEY` |

- 컨테이너 안에서 `localhost` 는 컨테이너 자신입니다. 호스트 DB·Ollama 는 `host.docker.internal` 로 씁니다. compose 가 BE·배치의 DB 호스트와 Ollama 주소를 덮어씁니다.
- AI 는 DB 접속 정보가 URL 하나라 호스트만 바꿀 수 없어서 루트 `AI_DATABASE_URL` 로 따로 지정합니다. 비밀번호에 `@ : / # %` 가 있으면 URL 인코딩이 필요합니다.
- DB 계정 구성은 [DATABASE.md 6장](../database/DATABASE.md) 참고. 현재 AI·배치는 `aidb` 를 씁니다 ([decisions/0004](../decisions/0004-임베딩-DB-현황.md)).
- 카카오맵: Kakao Developers → 앱 설정 → 플랫폼 → Web 에 `https://tp.ricebug.dev` 가 등록돼 있어야 지도가 뜹니다.

## 배포

```bash
cd ~/Project/Mini_Project_1
./scripts/deploy-macmini.sh develop
```

스크립트가 하는 일: `develop` 최신 받기 → 커밋 SHA 태그(`tp-*:<sha>`)로 이미지 빌드 → 같은 이미지에 `dev` 태그 → `docker compose up -d` 로 교체.
브랜치를 원격에 push 하기 전에는 그 브랜치로 실행할 수 없습니다 (`git fetch origin <브랜치>` 단계에서 실패).

## 상태 확인

```bash
docker compose ps                                   # 5개 Up, ai 는 healthy
docker compose logs --tail=50 be ai batch
curl -s localhost:8000/health                       # AI: ok, DB connected
curl -s -o /dev/null -w '%{http_code}\n' localhost/ # FE: 200
curl -s -o /dev/null -w '%{http_code}\n' "localhost/api/v1/map/places?regionCode=32"  # FE→BE 프록시: 200
docker compose run --rm batch python -m app.cli status
```

## 롤백

이전 커밋 SHA 태그 이미지가 남아 있으면 그 태그로 다시 띄웁니다.

```bash
docker images | grep '^tp-'            # 남아 있는 태그 확인
TAG=<이전 sha> docker compose up -d     # 빌드 없이 해당 태그로 교체
```

## 주의

- **재부팅:** colima 와 터널 모두 macOS 로그인 후에 뜹니다. 재부팅되면 로그인 전까지 사이트가 내려가 있습니다 (자동 로그인 여부는 미정).
- **배치 수집:** 매일 04:00 에 `aidb` 로 수집합니다. 다른 곳에서도 같은 키·DB 로 배치를 돌리면 호출 한도(개발계정 1,000건/일)와 데이터가 겹칩니다.
- **이미지 크기:** ai·batch 는 약 2GB (CPU 전용 torch 포함). 오래된 SHA 태그 이미지는 가끔 `docker image prune` 으로 정리합니다.
