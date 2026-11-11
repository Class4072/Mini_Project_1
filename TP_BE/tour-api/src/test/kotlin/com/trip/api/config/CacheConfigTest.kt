package com.trip.api.config

import com.trip.api.dto.PlaceMarkerResponse
import com.trip.core.domain.place.Category
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder

class CacheConfigTest {
    @Test
    fun `지도 마커 목록을 Redis에 JSON으로 썼다가 그대로 읽는다`() {
        val serializer = CacheConfig.placeMarkersSerializer(Jackson2ObjectMapperBuilder.json().build())
        val markers =
            listOf(
                PlaceMarkerResponse(1, "해운대해수욕장", Category.TOUR_SPOT, 35.1587, 129.1604, isIndoor = false),
                PlaceMarkerResponse(2, "달맞이길 카페", Category.CAFE, 35.1585, 129.182, isIndoor = true),
            )

        val bytes = requireNotNull(serializer.serialize(markers))

        assertThat(String(bytes)).contains("\"isIndoor\":true").doesNotContain("@class")
        assertThat(serializer.deserialize(bytes)).isEqualTo(markers)
    }
}
