package com.trip.api.client

import com.trip.api.common.Coordinate
import com.trip.api.config.KakaoMobilityProperties
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.web.reactive.function.client.WebClient
import java.util.concurrent.TimeUnit

class KakaoMobilityClientTest {
    private val server = MockWebServer()
    private val origin = Coordinate(lat = 35.1152, lng = 129.0422)
    private val destination = Coordinate(lat = 35.1587, lng = 129.1604)

    @BeforeEach
    fun setUp() = server.start()

    @AfterEach
    fun tearDown() = server.shutdown()

    private fun client(key: String = "test-key"): KakaoMobilityClient {
        val baseUrl = server.url("/").toString().trimEnd('/')
        return KakaoMobilityClient(WebClient.builder().baseUrl(baseUrl).build(), KakaoMobilityProperties(baseUrl, key))
    }

    private fun json(body: String) = MockResponse().setHeader("Content-Type", "application/json").setBody(body)

    @Test
    fun `경로의 거리·시간과 좌표 목록을 읽는다`() {
        server.enqueue(
            json(
                """
                {"trans_id":"x","routes":[{"result_code":0,"result_msg":"길찾기 성공",
                  "summary":{"distance":15234,"duration":1800},
                  "sections":[{"roads":[
                    {"vertexes":[129.0422,35.1152,129.05,35.12]},
                    {"vertexes":[129.1604,35.1587]}]}]}]}
                """.trimIndent(),
            ),
        )

        val route = runBlocking { client().findCarRoute(origin, destination) }

        assertThat(route?.distanceMeters).isEqualTo(15234)
        assertThat(route?.durationSeconds).isEqualTo(1800)
        assertThat(route?.path).containsExactly(
            Coordinate(35.1152, 129.0422),
            Coordinate(35.12, 129.05),
            Coordinate(35.1587, 129.1604),
        )
        val recorded = server.takeRequest(1, TimeUnit.SECONDS)
        assertThat(recorded?.getHeader("Authorization")).isEqualTo("KakaoAK test-key")
        assertThat(recorded?.requestUrl?.queryParameter("origin")).isEqualTo("129.0422,35.1152")
        assertThat(recorded?.requestUrl?.queryParameter("destination")).isEqualTo("129.1604,35.1587")
    }

    @Test
    fun `경로가 없거나 호출이 실패하면 null`() {
        server.enqueue(json("""{"routes":[{"result_code":104,"result_msg":"출발지와 도착지가 5 m 이내로 설정된 경우"}]}"""))
        assertThat(runBlocking { client().findCarRoute(origin, destination) }).isNull()

        server.enqueue(MockResponse().setResponseCode(401).setBody("""{"code":-401,"msg":"unauthorized"}"""))
        assertThat(runBlocking { client().findCarRoute(origin, destination) }).isNull()
    }

    @Test
    fun `키가 없으면 호출하지 않고 null`() {
        assertThat(runBlocking { client(key = "").findCarRoute(origin, destination) }).isNull()
        assertThat(server.requestCount).isZero()
    }
}
