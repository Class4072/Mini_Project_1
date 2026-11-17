# syntax=docker/dockerfile:1
# TP_BE 이미지: gradle로 tour-api bootJar 빌드 → JRE로 실행
#
# 빌드 시 루트 db/migration 을 함께 넣어야 한다 (tour-api/build.gradle.kts 의 processResources 가 ../db/migration 을 복사).
# 그래서 'db' 라는 추가 빌드 컨텍스트가 필요하다:
#   docker build --build-context db=./db -t tp-be ./TP_BE
# docker compose 에서는 additional_contexts 로 넘긴다.

# ── 1단계: 빌드 ─────────────────────────────────────────
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src/TP_BE

# ../db/migration 위치를 저장소와 똑같이 맞춘다
COPY --from=db migration /src/db/migration

COPY gradlew settings.gradle.kts build.gradle.kts gradle.properties ./
COPY gradle gradle
COPY tour-core tour-core
COPY tour-api tour-api

RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew --no-daemon :tour-api:bootJar -x test \
 && cp tour-api/build/libs/tour-api-*.jar /src/app.jar

# ── 2단계: 실행 ─────────────────────────────────────────
FROM eclipse-temurin:21-jre
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app app
COPY --from=build /src/app.jar app.jar
USER app

ENV TZ=Asia/Seoul \
    JAVA_OPTS="-XX:MaxRAMPercentage=75"
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
