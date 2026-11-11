package com.trip.api.service

import com.trip.api.client.AiDailyWeather
import com.trip.api.client.AiScheduleRequest
import com.trip.api.client.AiServiceClient
import com.trip.api.dto.TripCreateRequest
import com.trip.api.dto.TripDetailResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.slf4j.MDCContext
import kotlinx.coroutines.withContext
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service

/**
 * TR-001 AI 일정 생성 오케스트레이션 (BACKEND.md 4장).
 * DB 작업은 TripCommandService의 짧은 트랜잭션 두 번으로 나누고, 그 사이 AI 호출은 트랜잭션 밖에서 한다.
 * (AI 응답을 기다리는 동안 DB 커넥션을 잡고 있지 않도록)
 */
@Service
class TripService(
    private val tripCommandService: TripCommandService,
    private val tripQueryService: TripQueryService,
    private val aiServiceClient: AiServiceClient,
) {
    suspend fun createTripWithAiSchedule(request: TripCreateRequest): TripDetailResponse =
        // 코루틴이 스레드를 옮겨 다녀도 로그의 traceId가 유지되도록 MDC를 넘긴다
        withContext(MDCContext()) {
            val startedAt = System.nanoTime()
            val generating = withContext(Dispatchers.IO) { tripCommandService.createGeneratingTrip(request) }
            val placesCount =
                try {
                    val aiResponse = aiServiceClient.generateSchedule(generating.toAiRequest())
                    withContext(Dispatchers.IO) { tripCommandService.completeTrip(generating, aiResponse) }
                } catch (e: Exception) {
                    markFailed(generating.tripId, e)
                    throw e
                }
            val detail = withContext(Dispatchers.IO) { tripQueryService.getTripDetail(generating.tripId) }
            log.info(
                "여행 일정 생성 완료 | tripId={}, placesCount={}, durationMs={}",
                generating.tripId,
                placesCount,
                (System.nanoTime() - startedAt) / 1_000_000,
            )
            detail
        }

    // 요청이 취소된 경우에도 FAILED는 남긴다
    private suspend fun markFailed(tripId: Long, cause: Exception) {
        log.warn("여행 일정 생성 실패 | tripId={}, reason={}", tripId, cause.message)
        withContext(NonCancellable + Dispatchers.IO) {
            runCatching { tripCommandService.markFailed(tripId) }
                .onFailure { log.error("여행 실패 상태 저장 실패 | tripId={}", tripId, it) }
        }
    }

    private fun GeneratingTrip.toAiRequest(): AiScheduleRequest = AiScheduleRequest(
        regionCodes = listOf(command.regionCode),
        startDate = command.startDate,
        endDate = command.endDate,
        companionType = command.companionType.name,
        travelerCount = command.travelerCount,
        transport = command.transport.name,
        themes = command.themes.map { it.name },
        placesPerDay = command.placesPerDay.name,
        startTime = command.startTime.name,
        dailyWeathers =
        forecasts.map {
            AiDailyWeather(it.date, it.condition.name, it.temperature, it.precipitationProbability)
        },
    )

    companion object {
        private val log = LoggerFactory.getLogger(TripService::class.java)
    }
}
