import org.springframework.boot.gradle.tasks.run.BootRun

plugins {
    id("org.springframework.boot")
}

dependencies {
    implementation(project(":tour-core"))

    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-webflux") // AI·길찾기 호출용 WebClient
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-cache")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-slf4j")
    implementation("org.apache.poi:poi-ooxml:5.5.1") // PLAN-003 엑셀
    implementation("com.github.librepdf:openpdf:2.0.5") // PLAN-004 PDF

    // Apple Silicon 맥에서 Netty가 DNS 모듈을 못 찾아 남기는 ERROR 로그를 없앤다 (다른 OS에서는 쓰이지 않음)
    runtimeOnly("io.netty:netty-resolver-dns-native-macos::osx-aarch_64")

    testImplementation("org.testcontainers:junit-jupiter")
    testImplementation("org.testcontainers:postgresql")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
}

// 마이그레이션 SQL은 모노레포 루트 db/migration 한 곳에서 관리한다 (DATABASE.md 팀 합의 5번).
// 빌드할 때 classpath:db/migration 으로 복사해 Flyway가 읽는다.
tasks.processResources {
    from(rootProject.file("../db/migration")) {
        into("db/migration")
    }
}

// TP_BE/.env 를 읽도록 TP_BE 폴더에서 실행한다 (application.yml 의 spring.config.import)
tasks.named<BootRun>("bootRun") {
    workingDir = rootProject.projectDir
}
