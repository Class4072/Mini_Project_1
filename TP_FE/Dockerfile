# syntax=docker/dockerfile:1
# TP_FE 이미지: node로 빌드 → nginx로 정적 파일 서빙 + /api 를 BE로 프록시
# 빌드: docker build -t tp-fe ./TP_FE

# ── 1단계: 빌드 ─────────────────────────────────────────
FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .

# VITE_* 값은 Vite 특성상 빌드할 때 번들에 박힌다.
# - API 주소는 비워 두고 nginx 프록시(/api)를 쓰므로 실행 시 BACKEND_URL 로 바꿀 수 있다.
# - 카카오맵 JS 키는 원래 브라우저에 노출되는 키(도메인 제한)라 빌드 인자로 넣는다.
ARG VITE_API_BASE_URL=""
ARG VITE_KAKAO_MAP_API_KEY=""
ARG VITE_USE_MOCK="false"
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_KAKAO_MAP_API_KEY=$VITE_KAKAO_MAP_API_KEY \
    VITE_USE_MOCK=$VITE_USE_MOCK

RUN npm run build

# ── 2단계: 서빙 ─────────────────────────────────────────
FROM nginx:1.27-alpine

# nginx 공식 이미지는 시작할 때 /etc/nginx/templates/*.template 의 ${ENV} 를 치환한다 (실행 시 주입)
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

ENV BACKEND_URL=http://be:8080
EXPOSE 80
