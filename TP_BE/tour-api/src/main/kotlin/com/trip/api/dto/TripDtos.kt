package com.trip.api.dto

import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.annotation.JsonUnwrapped
import com.trip.api.common.KST
import com.trip.core.domain.place.Category
import com.trip.core.domain.region.Region
import com.trip.core.domain.schedule.Schedule
import com.trip.core.domain.schedule.SchedulePlace
import com.trip.core.domain.trip.CompanionType
import com.trip.core.domain.trip.PlacesPerDay
import com.trip.core.domain.trip.StartTimeOption
import com.trip.core.domain.trip.Theme
import com.trip.core.domain.trip.Transport
import com.trip.core.domain.trip.Trip
import com.trip.core.domain.trip.TripStatus
import com.trip.core.domain.weather.WeatherCondition
import jakarta.validation.constraints.Max
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotEmpty
import jakarta.validation.constraints.NotNull
import jakarta.validation.constraints.Size
import java.time.Duration
import java.time.LocalDate
import java.time.LocalTime
import java.time.OffsetDateTime

/**
 * TR-001 일정 생성 요청. 필드와 코드값은 FE·AI 일정 생성 요청 초안을 따른다 (DATABASE.md 3장).
 * 값이 빠졌을 때 검증 메시지를 돌려주려고 모두 nullable로 받는다.
 */
data class TripCreateRequest(
    @field:NotEmpty(message = "지역을 선택해 주세요.")
    @field:Size(max = 1, message = "지역은 하나만 선택할 수 있습니다.")
    val regionCodes: List<String>? = null,
    @field:NotNull(message = "출발일을 입력해 주세요.")
    val startDate: LocalDate? = null,
    @field:NotNull(message = "도착일을 입력해 주세요.")
    val endDate: LocalDate? = null,
    @field:NotNull(message = "동행 유형을 선택해 주세요.")
    val companionType: CompanionType? = null,
    @field:NotNull(message = "인원을 입력해 주세요.")
    @field:Min(value = 1, message = "인원은 1명 이상이어야 합니다.")
    @field:Max(value = 100, message = "인원은 100명 이하여야 합니다.")
    val travelerCount: Int? = null,
    @field:NotNull(message = "이동수단을 선택해 주세요.")
    val transport: Transport? = null,
    @field:Size(max = 3, message = "취향은 최대 3개까지 고를 수 있습니다.")
    val themes: List<Theme>? = null,
    val placesPerDay: PlacesPerDay? = null,
    val startTime: StartTimeOption? = null,
)

/** TR-003 여행 기본 정보 수정 */
data class TripUpdateRequest(
    @field:NotBlank(message = "여행 이름을 입력해 주세요.")
    @field:Size(max = 100, message = "여행 이름은 100자 이하로 입력해 주세요.")
    val title: String? = null,
    @field:Size(max = 2000, message = "메모는 2000자 이하로 입력해 주세요.")
    val memo: String? = null,
)

/** TR-003 응답, 그리고 TR-001·TR-002 응답의 여행 정보 부분 */
data class TripResponse(
    val tripId: Long,
    val title: String?,
    val status: TripStatus,
    val regionCode: String,
    val regionName: String?,
    val startDate: LocalDate,
    val endDate: LocalDate,
    val companionType: CompanionType,
    val travelerCount: Int,
    val transport: Transport,
    val themes: List<Theme>,
    val placesPerDay: PlacesPerDay,
    val startTime: StartTimeOption,
    val weatherSummary: String?,
    val memo: String?,
    val createdAt: OffsetDateTime,
) {
    companion object {
        fun of(trip: Trip, region: Region?): TripResponse = TripResponse(
            tripId = trip.id,
            title = trip.title,
            status = trip.status,
            regionCode = trip.regionCode,
            regionName = region?.name,
            startDate = trip.startDate,
            endDate = trip.endDate,
            companionType = trip.companionType,
            travelerCount = trip.travelerCount,
            transport = trip.transport,
            themes = trip.themes,
            placesPerDay = trip.placesPerDay,
            startTime = trip.startTime,
            weatherSummary = trip.weatherSummary,
            memo = trip.memo,
            createdAt = trip.createdAt.atZone(KST).toOffsetDateTime(),
        )
    }
}

/** TR-001·TR-002 응답: 여행 정보 + 일자별 일정 (JSON에서는 여행 정보 필드가 같은 단계에 펼쳐진다) */
data class TripDetailResponse(
    @get:JsonUnwrapped
    val trip: TripResponse,
    val dailySchedules: List<DailyScheduleResponse>,
) {
    companion object {
        fun of(trip: Trip, region: Region?): TripDetailResponse =
            TripDetailResponse(TripResponse.of(trip, region), trip.schedules.map(DailyScheduleResponse::of))
    }
}

data class DailyScheduleResponse(
    val scheduleId: Long,
    val dayNumber: Int,
    val date: LocalDate,
    val weatherCondition: WeatherCondition?,
    val temperature: Double?,
    val precipitationProbability: Int?,
    val places: List<SchedulePlaceResponse>,
) {
    companion object {
        fun of(schedule: Schedule): DailyScheduleResponse = DailyScheduleResponse(
            scheduleId = schedule.id,
            dayNumber = schedule.dayNumber,
            date = schedule.scheduleDate,
            weatherCondition = schedule.weatherCondition,
            temperature = schedule.temperature,
            precipitationProbability = schedule.precipitationProb,
            places = schedule.places.map(SchedulePlaceResponse::of),
        )
    }
}

data class SchedulePlaceResponse(
    val step: Int,
    val placeId: Long,
    val placeName: String,
    val category: Category,
    @get:JsonProperty("isIndoor")
    val isIndoor: Boolean,
    val address: String?,
    val imageUrl: String?,
    val latitude: Double,
    val longitude: Double,
    val startTime: LocalTime?,
    val endTime: LocalTime?,
    val stayTimeMinutes: Int?,
    val reason: String?,
) {
    companion object {
        fun of(schedulePlace: SchedulePlace): SchedulePlaceResponse {
            val place = schedulePlace.place
            return SchedulePlaceResponse(
                step = schedulePlace.visitOrder,
                placeId = place.id,
                placeName = place.name,
                category = place.category,
                isIndoor = place.indoor,
                address = place.address,
                imageUrl = place.imageUrl,
                latitude = place.latitude,
                longitude = place.longitude,
                startTime = schedulePlace.startTime,
                endTime = schedulePlace.endTime,
                stayTimeMinutes = stayMinutes(schedulePlace.startTime, schedulePlace.endTime),
                reason = schedulePlace.reason,
            )
        }

        // DATABASE.md 4.10: 체류 시간은 따로 저장하지 않고 end_time - start_time 으로 계산
        private fun stayMinutes(start: LocalTime?, end: LocalTime?): Int? =
            if (start != null && end != null && !end.isBefore(start)) {
                Duration.between(start, end).toMinutes().toInt()
            } else {
                null
            }
    }
}

/** TR-004 등 처리 결과 */
data class CommonResultResponse(val id: Long, val result: Boolean = true)
