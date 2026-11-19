# TP 문서 목차

TP 프로젝트 문서의 입구입니다. 여러 서비스에 걸친 공통 문서는 이 폴더(`TP_DOCS/`)에 두고,
서비스 전용 문서는 코드와 함께 각 서비스 폴더에 둡니다.

> 문서 위치 규칙: [decisions/0005-문서-위치.md](./decisions/0005-문서-위치.md)

## 공통 문서 (TP_DOCS)

| 폴더 | 무엇을 두나 | 주요 문서 |
| :--- | :--- | :--- |
| [architecture](./architecture/) | 시스템 구조, 서비스 간 흐름 | (현재는 루트 [ROOT.md](../ROOT.md)) |
| [database](./database/) | 통합 DB 스키마, 계정·권한 | [DATABASE.md](./database/DATABASE.md) |
| [api](./api/) | FE↔BE·BE↔AI API 계약, BE 요청 정리 | — |
| [infra](./infra/) | 도커, 맥미니 배포, 도메인·터널, CI | [맥미니 배포](./infra/macmini-deploy.md) · [Cloudflare 터널](./infra/cloudflare-tunnel.md) · [CI](./infra/ci.md) |
| [decisions](./decisions/) | 결정 기록 (왜 이렇게 정했는지) | [목록](./decisions/README.md) |
| [meetings](./meetings/) | 회의록 | — |
| [retrospective](./retrospective/) | 시행착오·개선점 (회고, 이력서 정리용) | — |

## 서비스 문서 (각 서비스 폴더)

| 서비스 | 문서 | 비고 |
| :--- | :--- | :--- |
| FE | [TP_FE/FRONTEND.md](../TP_FE/FRONTEND.md) | `TP_FE/CLAUDE.md` 가 이 문서를 불러온다 |
| BE | [TP_BE/BACKEND.md](../TP_BE/BACKEND.md) | |
| AI | [TP_AI/AI.md](../TP_AI/AI.md) | |
| 배치 | [TP_BATCH/BATCH.md](../TP_BATCH/BATCH.md) | |

## 루트 문서

- [README.md](../README.md): 저장소 소개, 폴더 구성, 비밀값 관리
- [ROOT.md](../ROOT.md): 아키텍처, 기술 스택, 협업 규칙

## 문서 작성 규칙

- 마크다운(`.md`)만 둡니다. xlsx·docx 같은 바이너리 문서는 구글드라이브에 둡니다.
- 비밀번호·API 키·IP 같은 값은 적지 않습니다. 키 **이름**만 적습니다.
- 파일을 옮길 때는 `git mv` 를 쓰고, 이 목차와 다른 문서의 링크를 같이 고칩니다.
