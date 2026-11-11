package com.trip.api.common

import com.trip.core.domain.place.GeoBox
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

data class Coordinate(val lat: Double, val lng: Double)

object Geo {
    private const val EARTH_RADIUS_METERS = 6_371_000.0

    /** 두 좌표 사이 직선 거리 (하버사인) */
    fun distanceMeters(from: Coordinate, to: Coordinate): Double {
        val dLat = Math.toRadians(to.lat - from.lat)
        val dLng = Math.toRadians(to.lng - from.lng)
        val a =
            sin(dLat / 2) * sin(dLat / 2) +
                cos(Math.toRadians(from.lat)) * cos(Math.toRadians(to.lat)) * sin(dLng / 2) * sin(dLng / 2)
        return 2 * EARTH_RADIUS_METERS * asin(sqrt(min(1.0, a)))
    }

    /** 중심에서 반경 radiusMeters를 덮는 위경도 사각형 */
    fun boundingBox(center: Coordinate, radiusMeters: Double): GeoBox {
        val dLat = Math.toDegrees(radiusMeters / EARTH_RADIUS_METERS)
        val dLng = dLat / cos(Math.toRadians(center.lat))
        return GeoBox(center.lat - dLat, center.lat + dLat, center.lng - dLng, center.lng + dLng)
    }
}
