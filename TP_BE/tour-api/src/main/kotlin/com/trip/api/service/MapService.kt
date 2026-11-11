package com.trip.api.service

import com.trip.api.client.KakaoMobilityClient
import com.trip.api.common.BusinessException
import com.trip.api.common.Coordinate
import com.trip.api.common.ErrorCode
import com.trip.api.common.Geo
import com.trip.api.config.CacheConfig
import com.trip.api.dto.NavigationResponse
import com.trip.api.dto.NavigationSource
import com.trip.api.dto.PlaceMarkerResponse
import com.trip.api.dto.PlaceSummaryResponse
import com.trip.api.dto.RoutePoint
import com.trip.api.dto.RoutePolylineResponse
import com.trip.core.domain.place.Category
import com.trip.core.domain.place.TourPlaceRepository
import com.trip.core.domain.schedule.ScheduleRepository
import org.springframework.cache.annotation.Cacheable
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import kotlin.math.roundToInt

@Service
class MapService(
    private val regionResolver: RegionResolver,
    private val tourPlaceRepository: TourPlaceRepository,
    private val scheduleRepository: ScheduleRepository,
    private val kakaoMobilityClient: KakaoMobilityClient,
) {
    /** MAP-001 카카오맵 마커용 장소 목록. 시도를 고르면 하위 시군구까지 포함한다. */
    @Cacheable(
        cacheNames = [CacheConfig.PLACE_MARKERS],
        key = "#regionCode + ':' + #category + ':' + #page + ':' + #size",
    )
    @Transactional(readOnly = true)
    fun getMarkers(regionCode: String, category: Category?, page: Int, size: Int): List<PlaceMarkerResponse> {
        val regionCodes = regionResolver.withChildren(regionResolver.resolve(regionCode))
        return tourPlaceRepository
            .findMarkers(regionCodes, category, page.toLong() * size, size.toLong())
            .map(PlaceMarkerResponse::of)
    }

    /** MAP-002 여행 일차별 동선 좌표 (방문 순서대로) */
    @Transactional(readOnly = true)
    fun getRoute(tripId: Long, dayNumber: Int): RoutePolylineResponse {
        val schedule =
            scheduleRepository.findActiveByTripIdAndDayNumber(tripId, dayNumber)
                ?: throw BusinessException(ErrorCode.SCHEDULE_NOT_FOUND)
        return RoutePolylineResponse(
            tripId = tripId,
            dayNumber = dayNumber,
            coordinates =
            schedule.places.map { RoutePoint(it.visitOrder, it.place.id, it.place.latitude, it.place.longitude) },
        )
    }

    /** MAP-004 반경 안의 장소를 가까운 순으로 */
    @Transactional(readOnly = true)
    fun findNearby(center: Coordinate, radiusMeters: Int, category: Category?, size: Int): List<PlaceSummaryResponse> =
        tourPlaceRepository
            .findNearestWithinBox(
                Geo.boundingBox(center, radiusMeters.toDouble()),
                center.lat,
                center.lng,
                category,
                size.toLong(),
            )
            .map { place -> place to Geo.distanceMeters(center, Coordinate(place.latitude, place.longitude)) }
            .filter { (_, distance) -> distance <= radiusMeters }
            .map { (place, distance) -> PlaceSummaryResponse.of(place, distance.roundToInt()) }

    /** MAP-005 장소 이름 검색 */
    @Transactional(readOnly = true)
    fun search(keyword: String, page: Int, size: Int): List<PlaceSummaryResponse> {
        val trimmed = keyword.trim()
        if (trimmed.isEmpty()) throw BusinessException(ErrorCode.INVALID_REQUEST, "검색어를 입력해 주세요.")
        return tourPlaceRepository
            .searchByName(trimmed, page.toLong() * size, size.toLong())
            .map { PlaceSummaryResponse.of(it) }
    }

    /**
     * MAP-003 출발-도착 길찾기. 카카오모빌리티(자동차) 결과를 쓰고,
     * 키가 없거나 실패하면 직선거리 × 우회 계수와 평균 속도로 추정한다.
     */
    suspend fun navigate(start: Coordinate, end: Coordinate): NavigationResponse {
        kakaoMobilityClient.findCarRoute(start, end)?.let { route ->
            return NavigationResponse(route.distanceMeters, route.durationSeconds, NavigationSource.KAKAO, route.path)
        }
        val distance = (Geo.distanceMeters(start, end) * ROAD_DETOUR_FACTOR).roundToInt()
        val duration = (distance / CAR_SPEED_METERS_PER_SECOND).roundToInt()
        return NavigationResponse(distance, duration, NavigationSource.ESTIMATE, listOf(start, end))
    }

    companion object {
        private const val ROAD_DETOUR_FACTOR = 1.3
        private const val CAR_SPEED_METERS_PER_SECOND = 30_000.0 / 3_600 // 시내 평균 30km/h
    }
}
