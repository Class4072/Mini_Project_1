package com.trip.api.service

import com.trip.api.client.AiSchedulePlace
import com.trip.api.client.AiScheduleResponse
import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.dto.CommonResultResponse
import com.trip.api.dto.TripCreateRequest
import com.trip.api.dto.TripResponse
import com.trip.api.dto.TripUpdateRequest
import com.trip.core.domain.place.TourPlaceRepository
import com.trip.core.domain.region.RegionRepository
import com.trip.core.domain.schedule.Schedule
import com.trip.core.domain.trip.CompanionType
import com.trip.core.domain.trip.PlacesPerDay
import com.trip.core.domain.trip.StartTimeOption
import com.trip.core.domain.trip.Theme
import com.trip.core.domain.trip.Transport
import com.trip.core.domain.trip.Trip
import com.trip.core.domain.trip.TripRepository
import com.trip.core.domain.weather.WeatherCondition
import com.trip.core.domain.weather.WeatherForecastRepository
import org.slf4j.LoggerFactory
import org.springframework.data.repository.findByIdOrNull
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Clock
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

/** 여행 쓰기. 메서드 하나가 트랜잭션 하나이고, 외부 호출은 하지 않는다. */
@Service
class TripCommandService(
    private val regionResolver: RegionResolver,
    private val regionRepository: RegionRepository,
    private val tripRepository: TripRepository,
    private val weatherForecastRepository: WeatherForecastRepository,
    private val tourPlaceRepository: TourPlaceRepository,
    private val clock: Clock,
) {
    /** TR-001 1단계: 요청 검증 → 여행을 GENERATING으로 저장 → 여행 기간 날씨 조회 (DATABASE.md 5.3) */
    @Transactional
    fun createGeneratingTrip(request: TripCreateRequest): GeneratingTrip {
        val command = request.toCommand()
        validate(command)
        val region = regionResolver.resolve(command.regionCode)
        val trip =
            tripRepository.save(
                Trip(
                    regionCode = region.regionCode,
                    startDate = command.startDate,
                    endDate = command.endDate,
                    companionType = command.companionType,
                    travelerCount = command.travelerCount,
                    transport = command.transport,
                    themes = command.themes,
                    placesPerDay = command.placesPerDay,
                    startTime = command.startTime,
                ),
            )
        val forecasts =
            weatherForecastRepository
                .findAllByRegionCodeAndForecastDateBetweenOrderByForecastDateAsc(
                    region.regionCode,
                    command.startDate,
                    command.endDate,
                ).map { DailyForecast(it.forecastDate, it.conditionCode, it.temperature, it.precipitationProb) }
        log.info(
            "여행 생성 요청 저장 | tripId={}, region={}, period={}~{}, forecastDays={}",
            trip.id,
            region.regionCode,
            command.startDate,
            command.endDate,
            forecasts.size,
        )
        return GeneratingTrip(trip.id, command, forecasts)
    }

    /**
     * TR-001 3단계: AI 응답을 일자별 일정으로 저장하고 COMPLETED로 바꾼다.
     * tour_places에 없는(또는 삭제된) 장소는 빼고 저장하며, 하나도 남지 않으면 실패로 본다.
     * 날씨는 예보가 있으면 예보 값을, 없으면 AI가 가정한 날씨를 복사해 둔다 (DATABASE.md 4.9).
     */
    @Transactional
    fun completeTrip(generating: GeneratingTrip, ai: AiScheduleResponse): Int {
        val trip =
            tripRepository.findByIdOrNull(generating.tripId)
                ?: throw BusinessException(ErrorCode.TRIP_NOT_FOUND)
        val aiDays = ai.dailySchedules.orEmpty().filter { it.day != null }.groupBy { it.day }
        val aiPlaces = aiDays.values.flatten().flatMap { it.places.orEmpty() }
        val placeIds = aiPlaces.mapNotNull { it.placeIdAsLong() }.toSet()
        val places =
            if (placeIds.isEmpty()) {
                emptyMap()
            } else {
                tourPlaceRepository.findAllByIdInAndDeletedFalse(
                    placeIds,
                ).associateBy {
                    it.id
                }
            }
        val forecasts = generating.forecasts.associateBy { it.date }

        (1..trip.dayCount).forEach { dayNumber ->
            val date = trip.startDate.plusDays(dayNumber - 1L)
            val aiDay = aiDays[dayNumber]?.first()
            val forecast = forecasts[date]
            val schedule =
                Schedule(
                    trip = trip,
                    dayNumber = dayNumber,
                    scheduleDate = date,
                    weatherCondition = forecast?.condition ?: WeatherCondition.fromCode(aiDay?.weatherCondition),
                    temperature = forecast?.temperature,
                    precipitationProb = forecast?.precipitationProbability,
                )
            aiDay
                ?.places
                .orEmpty()
                .sortedBy { it.step ?: Int.MAX_VALUE }
                .forEach { aiPlace ->
                    aiPlace.placeIdAsLong()?.let(places::get)?.let { place ->
                        schedule.addPlace(
                            place,
                            parseTime(aiPlace.startTime),
                            parseTime(aiPlace.endTime),
                            aiPlace.reason?.trim()?.ifBlank { null },
                        )
                    }
                }
            trip.addSchedule(schedule)
        }

        val savedCount = trip.schedules.sumOf { it.places.size }
        val skippedCount = aiPlaces.size - savedCount
        if (skippedCount > 0) {
            log.warn(
                "AI 응답 장소 중 tour_places에 없는 장소 제외 | tripId={}, skipped={}, sample={}",
                trip.id,
                skippedCount,
                aiPlaces.filter { it.placeIdAsLong()?.let(places::containsKey) != true }.take(5).map { it.placeId },
            )
        }
        if (savedCount == 0) {
            throw BusinessException(
                ErrorCode.AI_INVALID_RESPONSE,
                "AI가 돌려준 장소를 장소 목록(tour_places)에서 찾지 못해 일정을 저장하지 못했습니다.",
            )
        }
        trip.complete(
            title = ai.tripName?.trim()?.take(TITLE_MAX_LENGTH)?.ifBlank { null },
            weatherSummary = ai.weatherSummary?.trim()?.ifBlank { null },
        )
        return savedCount
    }

    @Transactional
    fun markFailed(tripId: Long) {
        tripRepository.findByIdOrNull(tripId)?.fail()
    }

    /** TR-003 */
    @Transactional
    fun updateTrip(tripId: Long, request: TripUpdateRequest): TripResponse {
        val trip = findActiveTrip(tripId)
        trip.updateInfo(
            title = requireNotNull(request.title).trim(),
            memo = request.memo?.trim()?.ifBlank { null },
        )
        return TripResponse.of(trip, regionRepository.findByIdOrNull(trip.regionCode))
    }

    /** TR-004 Soft Delete. 하위 일정은 여행과 함께 보이지 않게 된다. */
    @Transactional
    fun deleteTrip(tripId: Long): CommonResultResponse {
        findActiveTrip(tripId).delete(Instant.now(clock))
        log.info("여행 삭제 | tripId={}", tripId)
        return CommonResultResponse(tripId)
    }

    private fun findActiveTrip(tripId: Long): Trip =
        tripRepository.findByIdAndDeletedAtIsNull(tripId) ?: throw BusinessException(ErrorCode.TRIP_NOT_FOUND)

    private fun validate(command: TripCreateCommand) {
        val today = LocalDate.now(clock)
        val days = ChronoUnit.DAYS.between(command.startDate, command.endDate) + 1
        val error =
            when {
                command.startDate.isBefore(today) -> "출발일은 오늘($today) 이후여야 합니다."
                command.endDate.isBefore(command.startDate) -> "도착일은 출발일과 같거나 뒤여야 합니다."
                days > MAX_TRIP_DAYS -> "여행 기간은 최대 ${MAX_TRIP_DAYS}일입니다."
                command.companionType == CompanionType.SOLO && command.travelerCount != 1 -> "혼자 여행은 인원이 1명이어야 합니다."
                command.companionType != CompanionType.SOLO && command.travelerCount < 2 -> "동행이 있으면 인원은 2명 이상이어야 합니다."
                else -> null
            }
        error?.let { throw BusinessException(ErrorCode.INVALID_REQUEST, it) }
    }

    private fun TripCreateRequest.toCommand(): TripCreateCommand = TripCreateCommand(
        regionCode = requireNotNull(regionCodes).single(),
        startDate = requireNotNull(startDate),
        endDate = requireNotNull(endDate),
        companionType = requireNotNull(companionType),
        travelerCount = requireNotNull(travelerCount),
        transport = requireNotNull(transport),
        themes = themes.orEmpty().distinct(),
        placesPerDay = placesPerDay ?: PlacesPerDay.NORMAL,
        startTime = startTime ?: StartTimeOption.NORMAL,
    )

    private fun AiSchedulePlace.placeIdAsLong(): Long? = placeId?.trim()?.toLongOrNull()

    // AI는 "HH:mm"으로 준다. 형식이 다르면 시각 없이 저장한다.
    private fun parseTime(value: String?): LocalTime? = value?.trim()?.let { text ->
        runCatching { LocalTime.parse(text, AI_TIME_FORMAT) }
            .recoverCatching { LocalTime.parse(text) }
            .getOrNull()
    }

    companion object {
        /** AI 서비스 상한 (TP_AI API_SPEC.md 3.2, DATABASE.md 4.8 ck_trip_period) */
        const val MAX_TRIP_DAYS = 14
        private const val TITLE_MAX_LENGTH = 100
        private val AI_TIME_FORMAT = DateTimeFormatter.ofPattern("H:mm")
        private val log = LoggerFactory.getLogger(TripCommandService::class.java)
    }
}

/** 검증을 마친 일정 생성 요청. regionCode는 FE가 보낸 값 그대로다 (AI에 그대로 넘긴다). */
data class TripCreateCommand(
    val regionCode: String,
    val startDate: LocalDate,
    val endDate: LocalDate,
    val companionType: CompanionType,
    val travelerCount: Int,
    val transport: Transport,
    val themes: List<Theme>,
    val placesPerDay: PlacesPerDay,
    val startTime: StartTimeOption,
)

/** GENERATING으로 저장된 여행과 AI에 보낼 재료 */
data class GeneratingTrip(val tripId: Long, val command: TripCreateCommand, val forecasts: List<DailyForecast>)

data class DailyForecast(
    val date: LocalDate,
    val condition: WeatherCondition,
    val temperature: Double?,
    val precipitationProbability: Int?,
)
