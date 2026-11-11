package com.trip.api.support

import org.junit.jupiter.api.extension.ConditionEvaluationResult
import org.junit.jupiter.api.extension.ExecutionCondition
import org.junit.jupiter.api.extension.ExtensionContext
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.datasource.DriverManagerDataSource
import org.springframework.test.context.DynamicPropertyRegistry
import org.testcontainers.DockerClientFactory
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.utility.DockerImageName

/**
 * 통합 테스트용 DB.
 * - TEST_DB_URL 이 있으면 그 DB를 쓴다 (db/roles 스크립트로 계정을 준비해 둔 DB).
 *   계정: TEST_DB_USER/TEST_DB_PASSWORD (앱, 기본 tp_backend), TEST_FLYWAY_USER/TEST_FLYWAY_PASSWORD (소유자, 기본 tp_owner)
 * - 없으면 Docker로 pgvector/pgvector:pg16 컨테이너를 띄운다.
 * 앱은 운영과 같이 tp_backend로 접속하고 Flyway는 tp_owner로 실행한다. 권한이 모자라면 테스트가 실패한다.
 */
object TestDatabase {
    private val externalUrl: String? = env("TEST_DB_URL")

    val isAvailable: Boolean by lazy {
        externalUrl != null || runCatching { DockerClientFactory.instance().isDockerAvailable }.getOrDefault(false)
    }

    private val container: PgVectorContainer by lazy {
        PgVectorContainer(DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withInitScript("db/testcontainers-init.sql")
            .also { it.start() }
    }

    private val url: String
        get() = externalUrl ?: container.jdbcUrl
    private val appUser = env("TEST_DB_USER") ?: "tp_backend"
    private val appPassword = env("TEST_DB_PASSWORD") ?: "tp_backend"
    private val ownerUser = env("TEST_FLYWAY_USER") ?: "tp_owner"
    private val ownerPassword = env("TEST_FLYWAY_PASSWORD") ?: "tp_owner"

    fun registerProperties(registry: DynamicPropertyRegistry) {
        registry.add("spring.datasource.url") { url }
        registry.add("spring.datasource.username") { appUser }
        registry.add("spring.datasource.password") { appPassword }
        registry.add("spring.flyway.enabled") { "true" }
        registry.add("spring.flyway.user") { ownerUser }
        registry.add("spring.flyway.password") { ownerPassword }
    }

    /** 테스트 데이터는 테이블 소유자로 넣는다 (tp_backend는 장소·날씨 테이블에 쓰기 권한이 없다) */
    val ownerJdbc: JdbcTemplate by lazy { JdbcTemplate(DriverManagerDataSource(url, ownerUser, ownerPassword)) }

    private fun env(name: String): String? = System.getenv(name)?.takeIf { it.isNotBlank() }

    // Kotlin에서 PostgreSQLContainer의 자기 참조 제네릭을 쓰기 위한 서브클래스
    class PgVectorContainer(image: DockerImageName) : PostgreSQLContainer<PgVectorContainer>(image)
}

/** 테스트 DB를 쓸 수 없으면(TEST_DB_URL도 Docker도 없음) 통합 테스트를 건너뛴다 */
class RequiresTestDatabase : ExecutionCondition {
    override fun evaluateExecutionCondition(context: ExtensionContext): ConditionEvaluationResult =
        if (TestDatabase.isAvailable) {
            ConditionEvaluationResult.enabled("테스트 DB 사용 가능")
        } else {
            ConditionEvaluationResult.disabled("TEST_DB_URL이 없고 Docker도 없어 통합 테스트를 건너뜁니다.")
        }
}
