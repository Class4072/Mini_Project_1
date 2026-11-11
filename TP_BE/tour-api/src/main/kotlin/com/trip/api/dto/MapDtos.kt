package com.trip.api.dto

import com.fasterxml.jackson.annotation.JsonProperty
import com.trip.api.common.Coordinate
import com.trip.core.domain.place.Category
import com.trip.core.domain.place.TourPlace

/** MAP-001 지도 마커 */
data class PlaceMarkerResponse(
    val placeId: Long,
    val name: String,
    val category: Category,
    val latitude: Double,
    val longitude: Double,
    @get:JsonProperty("isIndoor")
    val isIndoor: Boolean,
) {
    companion object {
        fun of(place: TourPlace): PlaceMarkerResponse =
            PlaceMarkerResponse(place.id, place.name, place.category, place.latitude, place.longitude, place.indoor)
    }
}

/** MAP-004 주변 장소, MAP-005 검색 결과. distanceMeters는 MAP-004에서만 채운다. */
data class PlaceSummaryResponse(
    val placeId: Long,
    val name: String,
    val category: Category,
    val address: String?,
    val latitude: Double,
    val longitude: Double,
    @get:JsonProperty("isIndoor")
    val isIndoor: Boolean,
    val imageUrl: String?,
    val distanceMeters: Int? = null,
) {
    companion object {
        fun of(place: TourPlace, distanceMeters: Int? = null): PlaceSummaryResponse = PlaceSummaryResponse(
            placeId = place.id,
            name = place.name,
            category = place.category,
            address = place.address,
            latitude = place.latitude,
            longitude = place.longitude,
            isIndoor = place.indoor,
            imageUrl = place.imageUrl,
            distanceMeters = distanceMeters,
        )
    }
}

/** MAP-002 일차별 동선 (카카오맵 Polyline용, 방문 순서대로) */
data class RoutePolylineResponse(val tripId: Long, val dayNumber: Int, val coordinates: List<RoutePoint>)

data class RoutePoint(val step: Int, val placeId: Long, val lat: Double, val lng: Double)

/** MAP-003 길찾기. source가 ESTIMATE면 직선거리 기반 추정값이고 path는 출발·도착 두 점뿐이다. */
data class NavigationResponse(
    val distanceMeters: Int,
    val durationSeconds: Int,
    val source: NavigationSource,
    val path: List<Coordinate>,
)

enum class NavigationSource {
    KAKAO,
    ESTIMATE,
}
