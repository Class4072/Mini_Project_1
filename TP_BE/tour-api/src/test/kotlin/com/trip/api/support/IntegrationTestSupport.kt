package com.trip.api.support

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import com.trip.api.common.KST
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.extension.ExtendWith
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.http.MediaType
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.ResultActions
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import java.time.LocalDate

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@ExtendWith(RequiresTestDatabase::class)
abstract class IntegrationTestSupport {
    @Autowired
    protected lateinit var mockMvc: MockMvc

    @Autowired
    protected lateinit var objectMapper: ObjectMapper

    protected val fixtures: Fixtures by lazy { Fixtures(TestDatabase.ownerJdbc) }

    protected val tripStart: LocalDate = LocalDate.now(KST).plusDays(3)

    @BeforeEach
    fun resetState() {
        fixtures.truncateAll()
        AiServerStub.reset()
    }

    /** suspend 컨트롤러(TR-001, MAP-003)는 비동기로 처리되므로 asyncDispatch까지 이어서 결과를 받는다 */
    protected fun perform(builder: MockHttpServletRequestBuilder): ResultActions {
        val actions = mockMvc.perform(builder)
        val result = actions.andReturn()
        return if (result.request.isAsyncStarted) mockMvc.perform(asyncDispatch(result)) else actions
    }

    protected fun MockHttpServletRequestBuilder.jsonBody(value: Any): MockHttpServletRequestBuilder =
        contentType(MediaType.APPLICATION_JSON).content(objectMapper.writeValueAsString(value))

    protected fun ResultActions.data(): JsonNode =
        objectMapper.readTree(andReturn().response.contentAsByteArray).path("data")

    protected fun tripRequest(
        regionCode: String = "6",
        start: LocalDate = tripStart,
        end: LocalDate = tripStart.plusDays(1),
        companionType: String = "FRIENDS",
        travelerCount: Int = 3,
        transport: String = "PUBLIC_TRANSIT",
    ): Map<String, Any> = mapOf(
        "regionCodes" to listOf(regionCode),
        "startDate" to start.toString(),
        "endDate" to end.toString(),
        "companionType" to companionType,
        "travelerCount" to travelerCount,
        "transport" to transport,
        "themes" to listOf("FOOD", "NATURE"),
        "placesPerDay" to "NORMAL",
        "startTime" to "NORMAL",
    )

    /** 부산(TourAPI 지역코드 6)과 하위 해운대구 */
    protected fun givenBusan() {
        fixtures.region("PUSAN", "부산광역시", tourAreaCode = "6")
        fixtures.region("HAEUNDAE", "해운대구", level = "SIGUNGU", parent = "PUSAN")
    }

    /** AI가 days대로 일정을 짜도록 하고 여행을 만든다. 만든 여행의 상세 응답을 돌려준다. */
    protected fun createTrip(vararg days: AiDay): JsonNode {
        AiServerStub.respondJson(AiResponses.schedule(*days))
        return perform(post("/api/v1/trips").jsonBody(tripRequest(end = tripStart.plusDays(days.size - 1L))))
            .andExpect(status().isOk)
            .data()
    }

    companion object {
        @JvmStatic
        @DynamicPropertySource
        fun properties(registry: DynamicPropertyRegistry) {
            TestDatabase.registerProperties(registry)
            registry.add("ai.service.base-url") { AiServerStub.baseUrl }
        }
    }
}
