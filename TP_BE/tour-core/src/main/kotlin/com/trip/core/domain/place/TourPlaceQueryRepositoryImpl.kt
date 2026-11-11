package com.trip.core.domain.place

import com.querydsl.jpa.impl.JPAQueryFactory
import com.trip.core.domain.place.QTourPlace.tourPlace
import kotlin.math.cos

class TourPlaceQueryRepositoryImpl(private val queryFactory: JPAQueryFactory) : TourPlaceQueryRepository {
    override fun findMarkers(
        regionCodes: Collection<String>,
        category: Category?,
        offset: Long,
        limit: Long,
    ): List<TourPlace> = queryFactory
        .selectFrom(tourPlace)
        .where(
            tourPlace.regionCode.`in`(regionCodes),
            tourPlace.deleted.isFalse,
            category?.let { tourPlace.category.eq(it) },
        ).orderBy(tourPlace.id.asc())
        .offset(offset)
        .limit(limit)
        .fetch()

    override fun findNearestWithinBox(
        box: GeoBox,
        centerLatitude: Double,
        centerLongitude: Double,
        category: Category?,
        limit: Long,
    ): List<TourPlace> {
        // 좁은 범위에서는 평면 근사 거리(경도 차에 cos(위도)를 곱함)로 정렬해도 실제 거리 순서와 같다
        val lngScale = cos(Math.toRadians(centerLatitude))
        val dLat = tourPlace.latitude.subtract(centerLatitude)
        val dLng = tourPlace.longitude.subtract(centerLongitude).multiply(lngScale)
        return queryFactory
            .selectFrom(tourPlace)
            .where(
                tourPlace.latitude.between(box.minLatitude, box.maxLatitude),
                tourPlace.longitude.between(box.minLongitude, box.maxLongitude),
                tourPlace.deleted.isFalse,
                category?.let { tourPlace.category.eq(it) },
            ).orderBy(dLat.multiply(dLat).add(dLng.multiply(dLng)).asc(), tourPlace.id.asc())
            .limit(limit)
            .fetch()
    }

    // containsIgnoreCase는 키워드 안의 %, _ 를 이스케이프해서 LIKE 패턴으로 쓴다
    override fun searchByName(keyword: String, offset: Long, limit: Long): List<TourPlace> = queryFactory
        .selectFrom(tourPlace)
        .where(
            tourPlace.name.containsIgnoreCase(keyword),
            tourPlace.deleted.isFalse,
        ).orderBy(tourPlace.name.asc(), tourPlace.id.asc())
        .offset(offset)
        .limit(limit)
        .fetch()
}
