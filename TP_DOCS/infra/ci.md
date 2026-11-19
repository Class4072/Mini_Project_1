# CI (GitHub Actions)

설정 파일: [.github/workflows/ci.yml](../../.github/workflows/ci.yml)

## 언제 무엇이 도나

| 이벤트 | 동작 |
| :--- | :--- |
| PR (`develop`·`main` 대상) | 바뀐 서비스만 lint·test. 이미지 빌드는 Dockerfile·의존성 파일이 바뀐 서비스만 |
| `develop` push (PR 머지) | 바뀐 서비스 lint·test + **이미지 빌드 항상** + 캐시 저장 |

레지스트리 push 와 자동 배포(CD)는 하지 않습니다. 배포는 맥미니에서 수동으로 합니다 ([macmini-deploy.md](./macmini-deploy.md)).

| Job | PR 에서 하는 일 |
| :--- | :--- |
| FE | `npm ci` → `lint` → `test` → `build` (+ 이미지 빌드: Dockerfile·nginx·package*.json 변경 시) |
| BE | `./gradlew ktlintCheck test` (Testcontainers 가 러너의 Docker 사용) (+ 이미지: Dockerfile·*.gradle.kts·gradle/ 변경 시) |
| AI | `compileall` 문법 검사 (+ 이미지: Dockerfile·requirements.txt 변경 시) |
| BATCH | `compileall` 문법 검사 (+ 이미지: Dockerfile·requirements*.txt 변경 시) |

`ci.yml` 을 고친 PR 은 모든 서비스가 다 돕니다. `TP_DOCS` 등 서비스 폴더 밖 문서만 고친 PR 은 거의 돌지 않습니다.

## 캐시

- GitHub Actions 캐시는 **브랜치 단위**입니다. PR 은 대상 브랜치(`develop`)의 캐시를 읽을 수 있지만, PR 에서 만든 캐시는 `develop` 이 못 씁니다. 그래서 캐시 저장은 `develop` push 에서만 합니다.
- Gradle(`setup-gradle`)은 기본값이 "기본 브랜치(main)에서만 저장"이라 `cache-read-only` 를 develop 기준으로 지정했습니다.
- Docker 레이어 캐시(`type=gha`)는 서비스별 scope(`fe`·`be`·`ai`·`batch`)로 나눕니다. 저장소 캐시 한도는 10GB.

## 소요 시간 (2026-11-19 측정)

| Job | 개선 전 (develop push) | 개선 후 (develop push) |
| :--- | :--- | :--- |
| FE | 61s | 41s |
| BE | 372s | 162s (Gradle 캐시 적용 전 기준) |
| AI | 131s | 19s |
| BATCH | 132s | 23s |

## 알려진 개선 거리

- `be_image` 필터에 `db/migration/**`, `TP_BE/gradlew`, `TP_BE/gradle.properties` 가 빠져 있음 → 이 파일만 바뀐 PR 은 이미지 빌드를 건너뛰고 develop push 에서야 문제가 드러남
- AI·배치는 테스트가 저장소에 없어 문법 검사만 함 (pytest 추가 시 job 에 넣기)
