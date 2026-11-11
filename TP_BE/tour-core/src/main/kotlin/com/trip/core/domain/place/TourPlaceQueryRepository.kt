package com.trip.core.domain.place

/** QueryDSL로 구현하는 장소 조회 (조건이 선택적으로 붙는 쿼리) */
interface TourPlaceQueryRepository {
    /** MAP-001: 지역(하위 시군구 포함)·분류로 지도 마커용 장소 조회 */
    fun findMarkers(regionCodes: Collection<String>, category: Category?, offset: Long, limit: Long): List<TourPlace>

    /** MAP-004: 위경도 사각형 안의 장소를 중심에서 가까운 순으로 (정확한 반경 거리는 호출한 쪽에서 계산) */
    fun findNearestWithinBox(
        box: GeoBox,
        centerLatitude: Double,
        centerLongitude: Double,
        category: Category?,
        limit: Long,
    ): List<TourPlace>

    /** MAP-005: 장소 이름 키워드 검색 */
    fun searchByName(keyword: String, offset: Long, limit: Long): List<TourPlace>
}

data class GeoBox(val minLatitude: Double, val maxLatitude: Double, val minLongitude: Double, val maxLongitude: Double)
