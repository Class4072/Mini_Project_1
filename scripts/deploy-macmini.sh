#!/usr/bin/env bash
# 맥미니 개발 서버 배포: 최신 코드 받기 → 이미지 빌드(커밋 SHA 태그) → 컨테이너 교체
# 사용: ./scripts/deploy-macmini.sh [브랜치명, 기본 develop]
set -euo pipefail
export DOCKER_CONTEXT=colima   # 이 스크립트의 docker 명령은 항상 Colima로 보냄

BRANCH="${1:-develop}"
cd "$(dirname "$0")/.."

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

export TAG="$(git rev-parse --short HEAD)"
echo "▶ 빌드 태그: $TAG ($BRANCH)"

docker compose build
# 같은 이미지를 브랜치 이름 태그(dev)로도 남긴다 (롤백 시 SHA 태그로 되돌리면 됨)
for svc in fe be ai batch; do
  docker tag "tp-$svc:$TAG" "tp-$svc:dev"
done

docker compose up -d
docker compose ps
