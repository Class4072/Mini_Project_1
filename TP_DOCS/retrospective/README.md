# retrospective

시행착오와 개선점을 기록합니다. 프로젝트 회고와 이력서용 경험 정리의 재료가 됩니다.

- 파일 이름: `YYYY-MM-DD-주제.md`, 또는 기간별 `YYYY-MM.md`
- 형식: 무엇이 일어났나 → 원인 → 어떻게 해결했나 → 다음엔 이렇게

예시 거리 (2026-11 도커·배포 작업):
- 외장 SSD(ExFAT)에 저장소를 두었다가 `._*` 메타데이터 파일 때문에 git·Gradle 이 깨짐 → 내장 디스크로 이동
- colima 환경에 buildx 가 없어 `RUN --mount` 빌드 실패 → docker-buildx 설치
- CI 캐시가 브랜치 단위라 develop 에서 계속 miss → 캐시 저장을 develop push 로 한정
- 새 도메인 접속 시 DNS 캐시로 "주소 없음" → flushdns
