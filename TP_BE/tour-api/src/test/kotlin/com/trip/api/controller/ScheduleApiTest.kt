package com.trip.api.controller

import com.lowagie.text.pdf.PdfReader
import com.lowagie.text.pdf.parser.PdfTextExtractor
import com.trip.api.support.AiDay
import com.trip.api.support.AiStop
import com.trip.api.support.IntegrationTestSupport
import org.apache.poi.xssf.usermodel.XSSFWorkbook
import org.assertj.core.api.Assertions.assertThat
import org.hamcrest.Matchers.containsString
import org.hamcrest.Matchers.nullValue
import org.hamcrest.Matchers.startsWith
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.content
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.header
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import java.io.ByteArrayInputStream

class ScheduleApiTest : IntegrationTestSupport() {
    private var aquarium = 0L
    private var restaurant = 0L
    private var beach = 0L
    private var cafe = 0L
    private var tripId = 0L
    private var day1ScheduleId = 0L

    @BeforeEach
    fun setUp() {
        givenBusan()
        aquarium = fixtures.place("부산 아쿠아리움", "HAEUNDAE", category = "CULTURE", indoor = true, address = "부산 해운대구")
        restaurant = fixtures.place("해운대 대구탕", "HAEUNDAE", category = "RESTAURANT", indoor = true)
        beach = fixtures.place("해운대 해수욕장", "HAEUNDAE")
        cafe = fixtures.place("달맞이길 카페", "HAEUNDAE", category = "CAFE", indoor = true)
        val detail =
            createTrip(
                AiDay("RAIN", listOf(AiStop(aquarium, "10:30", "12:30"), AiStop(restaurant, "12:45", "13:45"))),
                AiDay("SUNNY", listOf(AiStop(beach))),
            )
        tripId = detail["tripId"].asLong()
        day1ScheduleId = detail["dailySchedules"][0]["scheduleId"].asLong()
    }

    @Test
    fun `하루 일정을 고치면 요청 순서대로 방문 순서를 다시 매겨 저장한다`() {
        val request =
            mapOf(
                "scheduleId" to day1ScheduleId,
                "places" to
                    listOf(
                        mapOf("placeId" to restaurant, "startTime" to "12:00", "endTime" to "13:00"),
                        mapOf("placeId" to cafe, "startTime" to "13:10", "endTime" to "14:00", "reason" to "식후 커피"),
                        mapOf("placeId" to aquarium),
                    ),
            )

        perform(post("/api/v1/schedules").jsonBody(request))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.tripId").value(tripId))
            .andExpect(jsonPath("$.data.scheduleId").value(day1ScheduleId))
            .andExpect(jsonPath("$.data.places.length()").value(3))
            .andExpect(jsonPath("$.data.places[0].placeName").value("해운대 대구탕"))
            .andExpect(jsonPath("$.data.places[1].step").value(2))
            .andExpect(jsonPath("$.data.places[1].reason").value("식후 커피"))
            .andExpect(jsonPath("$.data.places[1].stayTimeMinutes").value(50))
            .andExpect(jsonPath("$.data.places[2].startTime").value(nullValue()))

        perform(get("/api/v1/trips/$tripId"))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[0].placeName").value("해운대 대구탕"))
            .andExpect(jsonPath("$.data.dailySchedules[0].places[2].placeName").value("부산 아쿠아리움"))
            .andExpect(jsonPath("$.data.dailySchedules[1].places[0].placeName").value("해운대 해수욕장"))
    }

    @Test
    fun `없는 장소나 거꾸로 된 시각이 있으면 400이고 기존 일정은 그대로다`() {
        perform(
            post("/api/v1/schedules").jsonBody(
                mapOf(
                    "scheduleId" to day1ScheduleId,
                    "places" to listOf(mapOf("placeId" to 999_999)),
                ),
            ),
        )
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.code").value("PLACE_NOT_FOUND"))
        perform(
            post("/api/v1/schedules").jsonBody(
                mapOf(
                    "scheduleId" to day1ScheduleId,
                    "places" to listOf(mapOf("placeId" to beach, "startTime" to "15:00", "endTime" to "14:00")),
                ),
            ),
        ).andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.message", containsString("places[0]")))
        perform(post("/api/v1/schedules").jsonBody(mapOf("scheduleId" to 999_999, "places" to emptyList<Any>())))
            .andExpect(status().isNotFound)
            .andExpect(jsonPath("$.code").value("SCHEDULE_NOT_FOUND"))

        perform(get("/api/v1/trips/$tripId"))
            .andExpect(jsonPath("$.data.dailySchedules[0].places.length()").value(2))
    }

    @Test
    fun `공유 링크로 여행 전체를 읽기 전용으로 보고 메모는 빠진다`() {
        perform(put("/api/v1/trips/$tripId").jsonBody(mapOf("title" to "부산 여행", "memo" to "비밀 메모")))

        val first = perform(post("/api/v1/schedules/share").jsonBody(mapOf("scheduleId" to day1ScheduleId)))
        first
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.shareUrl", startsWith("https://trp.test/s/")))
        val token = first.data()["token"].asText()
        assertThat(token).hasSize(43)

        // 다시 만들면 같은 링크
        perform(post("/api/v1/schedules/share").jsonBody(mapOf("scheduleId" to day1ScheduleId)))
            .andExpect(jsonPath("$.data.token").value(token))

        perform(get("/api/v1/shares/$token"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.title").value("부산 여행"))
            .andExpect(jsonPath("$.data.memo").value(nullValue()))
            .andExpect(jsonPath("$.data.dailySchedules.length()").value(2))

        perform(get("/api/v1/shares/no-such-token")).andExpect(status().isNotFound)
        perform(delete("/api/v1/trips/$tripId"))
        perform(get("/api/v1/shares/$token"))
            .andExpect(status().isNotFound)
            .andExpect(jsonPath("$.code").value("SHARE_NOT_FOUND"))
    }

    @Test
    fun `엑셀로 여행 전체 일정을 내려받는다`() {
        val response =
            perform(get("/api/v1/schedules/$day1ScheduleId/export/excel"))
                .andExpect(status().isOk)
                .andExpect(content().contentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                .andExpect(header().string("Content-Disposition", containsString("filename*=UTF-8''")))
                .andReturn()
                .response

        XSSFWorkbook(ByteArrayInputStream(response.contentAsByteArray)).use { workbook ->
            val sheet = workbook.getSheet("여행 일정")
            val texts = sheet.flatMap { row -> row.map { it.toString() } }
            assertThat(texts).contains("비 오는 부산 1박 2일", "부산 아쿠아리움", "해운대 대구탕", "해운대 해수욕장", "문화시설")
        }
    }

    @Test
    fun `PDF로 여행 전체 일정을 내려받는다`() {
        val response =
            perform(get("/api/v1/schedules/$day1ScheduleId/export/pdf"))
                .andExpect(status().isOk)
                .andExpect(content().contentType("application/pdf"))
                .andReturn()
                .response

        val reader = PdfReader(response.contentAsByteArray)
        val text = (1..reader.numberOfPages).joinToString("\n") { PdfTextExtractor(reader).getTextFromPage(it) }
        assertThat(text).contains("부산 아쿠아리움", "해운대 해수욕장", "1일차")
        reader.close()
    }
}
