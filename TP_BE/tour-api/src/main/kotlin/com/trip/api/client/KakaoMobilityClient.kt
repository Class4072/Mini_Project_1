package com.trip.api.client

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty
import com.trip.api.common.Coordinate
import com.trip.api.config.KakaoMobilityProperties
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.withTimeout
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.core.codec.CodecException
import org.springframework.http.HttpHeaders
import org.springframework.stereotype.Component
import org.springframework.web.reactive.function.client.WebClient
import org.springframework.web.reactive.function.client.WebClientException
import org.springframework.web.reactive.function.client.awaitBody

/**
 * 카카오모빌리티 자동차 길찾기 (MAP-003). https://apis-navi.kakaomobility.com/v1/directions
 * 키가 없거나 호출이 실패하면 null을 돌려주고, 호출한 쪽이 직선거리로 추정한다.
 */
@Component
class KakaoMobilityClient(
    @param:Qualifier("kakaoMobilityWebClient") private val webClient: WebClient,
    private val properties: KakaoMobilityProperties,
) {
    suspend fun findCarRoute(origin: Coordinate, destination: Coordinate): CarRoute? {
        if (properties.restApiKey.isBlank()) return null
        return try {
            withTimeout(TIMEOUT_MILLIS) {
                webClient
                    .get()
                    .uri { builder ->
                        builder
                            .path(DIRECTIONS_PATH)
                            .queryParam("origin", "${origin.lng},${origin.lat}")
                            .queryParam("destination", "${destination.lng},${destination.lat}")
                            .queryParam("priority", "RECOMMEND")
                            .build()
                    }.header(HttpHeaders.AUTHORIZATION, "KakaoAK ${properties.restApiKey}")
                    .retrieve()
                    .awaitBody<KakaoDirectionsResponse>()
            }.toCarRoute()
        } catch (e: TimeoutCancellationException) {
            log.warn("카카오 길찾기 시간 초과, 직선거리로 추정")
            null
        } catch (e: WebClientException) {
            log.warn("카카오 길찾기 호출 실패, 직선거리로 추정 | error={}", e.message)
            null
        } catch (e: CodecException) {
            log.warn("카카오 길찾기 응답을 읽을 수 없음, 직선거리로 추정 | error={}", e.message)
            null
        }
    }

    private fun KakaoDirectionsResponse.toCarRoute(): CarRoute? {
        val route = routes?.firstOrNull() ?: return null
        if (route.resultCode != 0) {
            log.info("카카오 길찾기 경로 없음 | resultCode={}, message={}", route.resultCode, route.resultMsg)
            return null
        }
        val summary = route.summary ?: return null
        val path =
            route.sections
                .orEmpty()
                .flatMap { it.roads.orEmpty() }
                .flatMap { road -> road.vertexes.orEmpty().chunked(2).filter { it.size == 2 } }
                .map { (lng, lat) -> Coordinate(lat = lat, lng = lng) }
        return CarRoute(summary.distance ?: 0, summary.duration ?: 0, path)
    }

    companion object {
        private const val DIRECTIONS_PATH = "/v1/directions"
        private const val TIMEOUT_MILLIS = 5_000L
        private val log = LoggerFactory.getLogger(KakaoMobilityClient::class.java)
    }
}

data class CarRoute(val distanceMeters: Int, val durationSeconds: Int, val path: List<Coordinate>)

@JsonIgnoreProperties(ignoreUnknown = true)
data class KakaoDirectionsResponse(val routes: List<KakaoRoute>? = null)

@JsonIgnoreProperties(ignoreUnknown = true)
data class KakaoRoute(
    @param:JsonProperty("result_code") val resultCode: Int? = null,
    @param:JsonProperty("result_msg") val resultMsg: String? = null,
    val summary: KakaoRouteSummary? = null,
    val sections: List<KakaoRouteSection>? = null,
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class KakaoRouteSummary(val distance: Int? = null, val duration: Int? = null)

@JsonIgnoreProperties(ignoreUnknown = true)
data class KakaoRouteSection(val roads: List<KakaoRoad>? = null)

/** vertexes: [x1, y1, x2, y2, ...] (x = 경도, y = 위도) */
@JsonIgnoreProperties(ignoreUnknown = true)
data class KakaoRoad(val vertexes: List<Double>? = null)
