package com.trip.api.controller

import com.trip.api.support.AiDay
import com.trip.api.support.AiStop
import com.trip.api.support.IntegrationTestSupport
import org.assertj.core.api.Assertions.assertThat
import org.hamcrest.Matchers.containsInAnyOrder
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status

class MapApiTest : IntegrationTestSupport() {
    // 해운대 해수욕장 근처를 중심으로
    private val centerLat = 35.1587
    private val centerLng = 129.1604

    @BeforeEach
    fun setUp() {
        givenBusan()
        fixtures.region("SEOUL", "서울특별시", tourAreaCode = "1")
    }

    @Test
    fun `MAP-001 시도를 고르면 하위 시군구 장소까지 마커로 주고 삭제된 장소는 뺀다`() {
        fixtures.place("해운대 해수욕장", "HAEUNDAE")
        fixtures.place("달맞이길 카페", "HAEUNDAE", category = "CAFE")
        fixtures.place("부산역", "PUSAN")
        fixtures.place("폐업한 식당", "HAEUNDAE", category = "RESTAURANT", deleted = true)
        fixtures.place("경복궁", "SEOUL")

        // FE가 보내는 TourAPI 지역코드(6)와 region_code(PUSAN) 둘 다 받는다
        perform(get("/api/v1/map/places").param("regionCode", "6"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data[*].name", containsInAnyOrder("해운대 해수욕장", "달맞이길 카페", "부산역")))
        perform(get("/api/v1/map/places").param("regionCode", "HAEUNDAE").param("category", "CAFE"))
            .andExpect(jsonPath("$.data.length()").value(1))
            .andExpect(jsonPath("$.data[0].name").value("달맞이길 카페"))
            .andExpect(jsonPath("$.data[0].isIndoor").value(false))
        perform(get("/api/v1/map/places").param("regionCode", "PUSAN").param("page", "1").param("size", "2"))
            .andExpect(jsonPath("$.data.length()").value(1))

        perform(get("/api/v1/map/places").param("regionCode", "999"))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.code").value("REGION_NOT_FOUND"))
        perform(get("/api/v1/map/places").param("regionCode", "6").param("size", "0"))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
        perform(get("/api/v1/map/places").param("regionCode", "6").param("category", "MUSEUM"))
            .andExpect(status().isBadRequest)
    }

    @Test
    fun `MAP-002 여행 일차별 동선 좌표를 방문 순서대로 준다`() {
        val first = fixtures.place("첫 장소", "HAEUNDAE", latitude = 35.10, longitude = 129.10)
        val second = fixtures.place("둘째 장소", "HAEUNDAE", latitude = 35.20, longitude = 129.20)
        val tripId = createTrip(AiDay("SUNNY", listOf(AiStop(first), AiStop(second))))["tripId"].asLong()

        perform(get("/api/v1/map/route").param("tripId", "$tripId").param("dayNumber", "1"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data.coordinates.length()").value(2))
            .andExpect(jsonPath("$.data.coordinates[0].placeId").value(first))
            .andExpect(jsonPath("$.data.coordinates[0].lat").value(35.10))
            .andExpect(jsonPath("$.data.coordinates[1].lng").value(129.20))
        perform(get("/api/v1/map/route").param("tripId", "$tripId").param("dayNumber", "5"))
            .andExpect(status().isNotFound)
    }

    @Test
    fun `MAP-004 반경 안의 장소만 가까운 순으로 거리와 함께 준다`() {
        fixtures.place("5km 밖", "HAEUNDAE", latitude = centerLat + 0.045, longitude = centerLng)
        fixtures.place("1km", "HAEUNDAE", latitude = centerLat + 0.009, longitude = centerLng)
        fixtures.place("100m", "HAEUNDAE", latitude = centerLat + 0.0009, longitude = centerLng)

        val nearby =
            perform(get("/api/v1/map/nearby").param("lat", "$centerLat").param("lng", "$centerLng"))
                .andExpect(status().isOk)
                .data()
        assertThat(nearby.map { it["name"].asText() }).containsExactly("100m", "1km")
        assertThat(nearby[0]["distanceMeters"].asInt()).isBetween(95, 105)
        assertThat(nearby[1]["distanceMeters"].asInt()).isBetween(990, 1010)

        perform(
            get("/api/v1/map/nearby").param("lat", "$centerLat").param("lng", "$centerLng").param("radiusMeter", "200"),
        )
            .andExpect(jsonPath("$.data.length()").value(1))
        perform(get("/api/v1/map/nearby").param("lat", "91").param("lng", "$centerLng"))
            .andExpect(status().isBadRequest)
    }

    @Test
    fun `MAP-005 이름으로 검색하고 검색어의 퍼센트 기호는 글자 그대로 찾는다`() {
        fixtures.place("해운대 해수욕장", "HAEUNDAE")
        fixtures.place("해운대 시장", "HAEUNDAE")
        fixtures.place("100% 오션뷰 카페", "HAEUNDAE", category = "CAFE")
        fixtures.place("광안리 해수욕장", "PUSAN")

        perform(get("/api/v1/map/search").param("keyword", " 해운대 "))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.data[*].name", containsInAnyOrder("해운대 해수욕장", "해운대 시장")))
        perform(get("/api/v1/map/search").param("keyword", "%"))
            .andExpect(jsonPath("$.data.length()").value(1))
            .andExpect(jsonPath("$.data[0].name").value("100% 오션뷰 카페"))
        perform(get("/api/v1/map/search").param("keyword", " "))
            .andExpect(status().isBadRequest)
    }

    @Test
    fun `MAP-003 길찾기 키가 없으면 직선거리로 추정한다`() {
        val response =
            perform(
                get("/api/v1/map/navigation")
                    .param("startLat", "35.1152")
                    .param("startLng", "129.0422")
                    .param("endLat", "35.1587")
                    .param("endLng", "129.1604"),
            ).andExpect(status().isOk)
                .data()

        assertThat(response["source"].asText()).isEqualTo("ESTIMATE")
        assertThat(response["distanceMeters"].asInt()).isGreaterThan(11_000) // 직선 약 11.8km × 1.3
        assertThat(response["durationSeconds"].asInt()).isGreaterThan(0)
        assertThat(response["path"].size()).isEqualTo(2)
    }
}
