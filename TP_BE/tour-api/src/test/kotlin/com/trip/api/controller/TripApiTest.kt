package com.trip.api.controller

import com.trip.api.support.AiDay
import com.trip.api.support.AiResponses
import com.trip.api.support.AiServerStub
import com.trip.api.support.AiStop
import com.trip.api.support.IntegrationTestSupport
import okhttp3.mockwebserver.MockResponse
import org.assertj.core.api.Assertions.assertThat
import org.hamcrest.Matchers.contains
import org.hamcrest.Matchers.containsString
import org.hamcrest.Matchers.nullValue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.header
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status

class TripApiTest : IntegrationTestSupport() {
    @BeforeEach
    fun setUp() {
        givenBusan()
    }

    @Test
    fun `여행을 만들면 AI 일정을 일자별로 저장하고 상세 정보를 돌려준다`() {
        val aquarium = fixtures.place("부산 아쿠아리움", "HAEUNDAE", category = "CULTURE", indoor = true)
        val restaurant = fixtures.place("해운대 대구탕", "HAEUNDAE", category = "RESTAURANT", indoor = true)
        val beach = fixtures.place("해운대 해수욕장", "HAEUNDAE")
        fixtures.weather("PUSAN", tripStart, "RAIN", 16.0, 80) // 2일차 예보는 없음
        AiServerStub.respondJson(
            AiResponses.schedule(
                AiDay(
                    "RAIN",
                    listOf(AiStop(aquarium, "10:30", "12:30"), AiStop(restaurant.toString(), "12:45", "13:45")),
                ),
                AiDay("SUNNY", listOf(AiStop(beach))),
            ),
        )

        perform(post("/api/v1/trips").jsonBody(tripRequest()))
            .andExpect(status().isOk)
            .andExpect(header().exists("X-Trace-Id"))
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.data.status").value("COMPLETED"))
            .andExpect(jsonPath("$.data.title").value("비 오는 부산 1박 2일"))
            .andExpect(jsonPath("$.data.regionCode").value("PUSAN"))
            .andExpect(jsonPath("$.data.regionName").value("부산광역시"))
            .andExpect(jsonPath("$.data.themes", contains("FOOD", "NATURE")))
            .andExpect(jsonPath("$.data.dailySchedules.length()").value(2))
            .andExpect(jsonPath("$.data.dailySchedules[0].weatherCondition").value("RAIN"))
            .andExpect(jsonPath("$.data.dailySchedules[0].temperature").value(16.0))
            .andExpect(jsonPath("$.data.dailySchedules[0].places.length()").value(2))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].step").value(1))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].placeName").value("부산 아쿠아리움"))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].category").value("CULTURE"))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].isIndoor").value(true))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].startTime").value("10:30"))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].stayTimeMinutes").value(120))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[1].placeName").value("해운대 대구탕"))
            // 예보가 없는 날은 AI가 가정한 날씨를 남긴다
            .andExpect(jsonPath("$.data.dailySchedules[1].weatherCondition").value("SUNNY"))
            .andExpect(jsonPath("$.data.dailySchedules[1].temperature").value(nullValue()))

        // FE 요청 필드를 그대로 넘기고, 예보가 있는 날짜의 날씨만 붙인다
        val aiRequest = objectMapper.readTree(AiServerStub.takeRequest().body.readUtf8())
        assertThat(aiRequest["regionCodes"].map { it.asText() }).containsExactly("6")
        assertThat(aiRequest["companionType"].asText()).isEqualTo("FRIENDS")
        assertThat(aiRequest["travelerCount"].asInt()).isEqualTo(3)
        assertThat(aiRequest["transport"].asText()).isEqualTo("PUBLIC_TRANSIT")
        assertThat(aiRequest["themes"].map { it.asText() }).containsExactly("FOOD", "NATURE")
        assertThat(aiRequest["dailyWeathers"].size()).isEqualTo(1)
        assertThat(aiRequest["dailyWeathers"][0]["date"].asText()).isEqualTo(tripStart.toString())
        assertThat(aiRequest["dailyWeathers"][0]["condition"].asText()).isEqualTo("RAIN")
        assertThat(aiRequest["dailyWeathers"][0]["precipitationProbability"].asInt()).isEqualTo(80)
    }

    @Test
    fun `AI가 오류를 돌려주면 502로 응답하고 여행은 FAILED로 남는다`() {
        AiServerStub.respond(MockResponse().setResponseCode(500).setBody("""{"detail":"LLM 오류"}"""))

        perform(post("/api/v1/trips").jsonBody(tripRequest()))
            .andExpect(status().isBadGateway)
            .andExpect(jsonPath("$.success").value(false))
            .andExpect(jsonPath("$.code").value("AI_SERVICE_ERROR"))

        assertThat(fixtures.tripStatuses()).containsExactly("FAILED")
    }

    @Test
    fun `AI가 장소 목록에 없는 장소만 돌려주면 일정을 저장하지 않고 FAILED로 남긴다`() {
        // 지금 AI 브랜치처럼 travel_spots의 문자열 ID를 돌려주는 경우
        AiServerStub.respondJson(AiResponses.schedule(AiDay("SUNNY", listOf(AiStop("p101"), AiStop(999_999)))))

        perform(post("/api/v1/trips").jsonBody(tripRequest(end = tripStart)))
            .andExpect(status().isBadGateway)
            .andExpect(jsonPath("$.code").value("AI_INVALID_RESPONSE"))

        assertThat(fixtures.tripStatuses()).containsExactly("FAILED")
        assertThat(fixtures.count("schedules")).isZero()
    }

    @Test
    fun `AI가 돌려준 장소 중 장소 목록에 없는 것과 삭제된 것은 빼고 저장한다`() {
        val beach = fixtures.place("해운대 해수욕장", "HAEUNDAE")
        val closed = fixtures.place("폐업한 카페", "HAEUNDAE", category = "CAFE", deleted = true)

        createTrip(AiDay("SUNNY", listOf(AiStop("p101"), AiStop(closed), AiStop(beach))))
            .let { detail ->
                assertThat(detail["status"].asText()).isEqualTo("COMPLETED")
                val places = detail["dailySchedules"][0]["places"]
                assertThat(places.map { it["placeName"].asText() }).containsExactly("해운대 해수욕장")
                assertThat(places[0]["step"].asInt()).isEqualTo(1)
            }
    }

    @Test
    fun `요청 값이 잘못되면 AI를 부르지 않고 400으로 이유를 알려준다`() {
        perform(post("/api/v1/trips").jsonBody(tripRequest(regionCode = "999")))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.code").value("REGION_NOT_FOUND"))
        perform(
            post("/api/v1/trips").jsonBody(tripRequest(start = tripStart.minusDays(10), end = tripStart.minusDays(9))),
        )
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.message", containsString("출발일")))
        perform(post("/api/v1/trips").jsonBody(tripRequest(end = tripStart.plusDays(14))))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.message", containsString("최대 14일")))
        perform(post("/api/v1/trips").jsonBody(tripRequest(companionType = "SOLO", travelerCount = 3)))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.message", containsString("혼자")))
        perform(post("/api/v1/trips").jsonBody(tripRequest(transport = "BUS")))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
            .andExpect(jsonPath("$.message", containsString("transport")))
        perform(post("/api/v1/trips").jsonBody(tripRequest() - "companionType"))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.message", containsString("companionType")))

        assertThat(AiServerStub.requestCount).isZero()
        assertThat(fixtures.count("trips")).isZero()
    }

    @Test
    fun `여행을 조회하고 이름과 메모를 고치고 삭제한다`() {
        val beach = fixtures.place("해운대 해수욕장", "HAEUNDAE")
        val tripId = createTrip(AiDay("SUNNY", listOf(AiStop(beach))))["tripId"].asLong()

        perform(get("/api/v1/trips/$tripId"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.tripId").value(tripId))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].placeName").value("해운대 해수욕장"))

        perform(put("/api/v1/trips/$tripId").jsonBody(mapOf("title" to "  우리 부산 여행 ", "memo" to "숙소 체크인 3시")))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.title").value("우리 부산 여행"))
            .andExpect(jsonPath("$.data.memo").value("숙소 체크인 3시"))
            .andExpect(jsonPath("$.data.dailySchedules").doesNotExist())
        perform(put("/api/v1/trips/$tripId").jsonBody(mapOf("title" to " ")))
            .andExpect(status().isBadRequest)

        perform(delete("/api/v1/trips/$tripId"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.id").value(tripId))
        perform(get("/api/v1/trips/$tripId"))
            .andExpect(status().isNotFound)
            .andExpect(jsonPath("$.code").value("TRIP_NOT_FOUND"))
        assertThat(fixtures.isSoftDeleted(tripId)).isTrue()
    }
}
