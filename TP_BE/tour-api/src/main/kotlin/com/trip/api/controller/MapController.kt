package com.trip.api.controller

import com.trip.api.common.ApiResponse
import com.trip.api.common.Coordinate
import com.trip.api.dto.NavigationResponse
import com.trip.api.dto.PlaceMarkerResponse
import com.trip.api.dto.PlaceSummaryResponse
import com.trip.api.dto.RoutePolylineResponse
import com.trip.api.service.MapService
import com.trip.core.domain.place.Category
import jakarta.validation.constraints.DecimalMax
import jakarta.validation.constraints.DecimalMin
import jakarta.validation.constraints.Max
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Size
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

/** 지도 및 장소 탐색 API (BACKEND.md 3.3). page는 0부터 센다. */
@RestController
@RequestMapping("/api/v1/map")
class MapController(private val mapService: MapService) {
    /** MAP-001 카카오맵 마커용 장소 목록. regionCode는 region_code 또는 TourAPI 지역코드 */
    @GetMapping("/places")
    fun getPlaces(
        @RequestParam @NotBlank @Size(max = 20) regionCode: String,
        @RequestParam(required = false) category: Category?,
        @RequestParam(defaultValue = "0") @Min(0) page: Int,
        @RequestParam(defaultValue = "100") @Min(1) @Max(500) size: Int,
    ): ApiResponse<List<PlaceMarkerResponse>> =
        ApiResponse.success(mapService.getMarkers(regionCode, category, page, size))

    /** MAP-002 여행 일차별 Polyline 동선 */
    @GetMapping("/route")
    fun getRoute(
        @RequestParam tripId: Long,
        @RequestParam @Min(1) dayNumber: Int,
    ): ApiResponse<RoutePolylineResponse> = ApiResponse.success(mapService.getRoute(tripId, dayNumber))

    /** MAP-003 출발-도착 길찾기 (시간, 거리) */
    @GetMapping("/navigation")
    suspend fun navigate(
        @RequestParam @DecimalMin("-90") @DecimalMax("90") startLat: Double,
        @RequestParam @DecimalMin("-180") @DecimalMax("180") startLng: Double,
        @RequestParam @DecimalMin("-90") @DecimalMax("90") endLat: Double,
        @RequestParam @DecimalMin("-180") @DecimalMax("180") endLng: Double,
    ): ApiResponse<NavigationResponse> =
        ApiResponse.success(mapService.navigate(Coordinate(startLat, startLng), Coordinate(endLat, endLng)))

    /** MAP-004 내 주변(반경 radiusMeter) 장소, 가까운 순 */
    @GetMapping("/nearby")
    fun getNearby(
        @RequestParam @DecimalMin("-90") @DecimalMax("90") lat: Double,
        @RequestParam @DecimalMin("-180") @DecimalMax("180") lng: Double,
        @RequestParam(defaultValue = "3000") @Min(100) @Max(20000) radiusMeter: Int,
        @RequestParam(required = false) category: Category?,
        @RequestParam(defaultValue = "30") @Min(1) @Max(100) size: Int,
    ): ApiResponse<List<PlaceSummaryResponse>> =
        ApiResponse.success(mapService.findNearby(Coordinate(lat, lng), radiusMeter, category, size))

    /** MAP-005 키워드 장소 검색 */
    @GetMapping("/search")
    fun search(
        @RequestParam @NotBlank @Size(max = 50) keyword: String,
        @RequestParam(defaultValue = "0") @Min(0) page: Int,
        @RequestParam(defaultValue = "20") @Min(1) @Max(100) size: Int,
    ): ApiResponse<List<PlaceSummaryResponse>> = ApiResponse.success(mapService.search(keyword, page, size))
}
