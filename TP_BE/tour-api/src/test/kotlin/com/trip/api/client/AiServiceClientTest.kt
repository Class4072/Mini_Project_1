package com.trip.api.client

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.config.AiServiceProperties
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.web.reactive.function.client.WebClient
import java.time.LocalDate
import java.util.concurrent.TimeUnit

class AiServiceClientTest {
    private val server = MockWebServer()

    @BeforeEach
    fun setUp() = server.start()

    @AfterEach
    fun tearDown() = server.shutdown()

    private fun client(timeoutSeconds: Long = 2): AiServiceClient {
        val baseUrl = server.url("/").toString().trimEnd('/')
        return AiServiceClient(
            WebClient.builder().baseUrl(baseUrl).build(),
            AiServiceProperties(baseUrl, timeoutSeconds),
        )
    }

    private val request =
        AiScheduleRequest(
            regionCodes = listOf("6"),
            startDate = LocalDate.of(2026, 11, 20),
            endDate = LocalDate.of(2026, 11, 21),
            companionType = "FRIENDS",
            travelerCount = 3,
            transport = "PUBLIC_TRANSIT",
            themes = listOf("FOOD"),
            placesPerDay = "NORMAL",
            startTime = "NORMAL",
            dailyWeathers = listOf(AiDailyWeather(LocalDate.of(2026, 11, 20), "RAIN", 16.0, 80)),
        )

    private fun call(client: AiServiceClient = client()) = runBlocking { client.generateSchedule(request) }

    @Test
    fun `일정 생성 요청을 보내고 숫자와 문자열 placeId를 모두 받는다`() {
        server.enqueue(
            MockResponse().setHeader("Content-Type", "application/json").setBody(
                """
                {"tripName":"부산 여행","weatherSummary":"비","unknownField":1,
                 "dailySchedules":[{"day":1,"date":"2026-11-20","weatherCondition":"RAIN","totalDayDistanceKm":3.2,
                   "places":[{"step":1,"placeId":1024,"placeName":"A","startTime":"10:00","endTime":"11:00"},
                             {"step":2,"placeId":"p101","placeName":"B"}]}]}
                """.trimIndent(),
            ),
        )

        val response = call()

        assertThat(response.tripName).isEqualTo("부산 여행")
        assertThat(
            response.dailySchedules.orEmpty().single().places.orEmpty().map {
                it.placeId
            },
        ).containsExactly("1024", "p101")
        val recorded = server.takeRequest(1, TimeUnit.SECONDS)
        assertThat(recorded?.path).isEqualTo("/api/v1/ai/schedule")
        val body = recorded?.body?.readUtf8().orEmpty()
        assertThat(body).contains("\"regionCodes\":[\"6\"]", "\"startDate\":\"2026-11-20\"", "\"condition\":\"RAIN\"")
    }

    @Test
    fun `AI가 오류 상태로 답하면 AI_SERVICE_ERROR`() {
        server.enqueue(MockResponse().setResponseCode(500).setBody("""{"detail":"LLM 오류"}"""))
        assertThatThrownBy { call() }
            .isInstanceOf(BusinessException::class.java)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.AI_SERVICE_ERROR)

        server.enqueue(MockResponse().setResponseCode(422).setBody("""{"detail":[{"msg":"field required"}]}"""))
        assertThatThrownBy { call() }.extracting("errorCode").isEqualTo(ErrorCode.AI_SERVICE_ERROR)
    }

    @Test
    fun `정해진 시간 안에 답이 없으면 AI_SERVICE_TIMEOUT`() {
        server.enqueue(MockResponse().setBody("{}").setHeadersDelay(3, TimeUnit.SECONDS))
        assertThatThrownBy { call(client(timeoutSeconds = 1)) }
            .extracting("errorCode")
            .isEqualTo(ErrorCode.AI_SERVICE_TIMEOUT)
    }

    @Test
    fun `JSON이 아닌 응답은 AI_INVALID_RESPONSE`() {
        server.enqueue(MockResponse().setHeader("Content-Type", "application/json").setBody("not json"))
        assertThatThrownBy { call() }.extracting("errorCode").isEqualTo(ErrorCode.AI_INVALID_RESPONSE)
    }

    @Test
    fun `AI 서비스에 연결할 수 없으면 AI_SERVICE_ERROR`() {
        val client = client()
        server.shutdown()
        assertThatThrownBy { call(client) }.extracting("errorCode").isEqualTo(ErrorCode.AI_SERVICE_ERROR)
    }
}
