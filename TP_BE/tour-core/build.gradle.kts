plugins {
    `java-library`
    kotlin("plugin.jpa")
    kotlin("kapt")
}

val querydslVersion = "7.7"

dependencies {
    api("org.springframework.boot:spring-boot-starter-data-jpa")
    api("io.github.openfeign.querydsl:querydsl-jpa:$querydslVersion")
    kapt("io.github.openfeign.querydsl:querydsl-apt:$querydslVersion:jpa")
    kapt("jakarta.persistence:jakarta.persistence-api")
    kapt("jakarta.annotation:jakarta.annotation-api")
    runtimeOnly("org.postgresql:postgresql")
}

// JPA 지연 로딩 프록시를 만들 수 있도록 엔티티 클래스를 open으로 컴파일한다
allOpen {
    annotation("jakarta.persistence.Entity")
    annotation("jakarta.persistence.MappedSuperclass")
    annotation("jakarta.persistence.Embeddable")
}
