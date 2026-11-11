package com.trip.api.client

import com.fasterxml.jackson.annotation.JsonFormat
import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import java.time.LocalDate

// AI 서비스 POST /api/v1/ai/schedule 요청·응답 (TP_AI API_SPEC.md 3장, 5.2)

/**
 * FE 일정 생성 요청 필드를 그대로 넘기고, 백엔드가 조회한 날씨만 붙인다.
 * 날짜는 AI(Pydantic date)가 받는 "YYYY-MM-DD" 문자열로 고정한다 (전역 Jackson 설정과 무관하게).
 */
data class AiScheduleRequest(
    val regionCodes: List<String>,
    @get:JsonFormat(shape = JsonFormat.Shape.STRING)
    val startDate: LocalDate,
    @get:JsonFormat(shape = JsonFormat.Shape.STRING)
    val endDate: LocalDate,
    val companionType: String,
    val travelerCount: Int,
    val transport: String,
    val themes: List<String>,
    val placesPerDay: String,
    val startTime: String,
    /** 예보가 있는 날짜만 담는다. 없는 날은 AI가 계절로 추론한다 (DATABASE.md 4.6) */
    val dailyWeathers: List<AiDailyWeather>,
)

data class AiDailyWeather(
    @get:JsonFormat(shape = JsonFormat.Shape.STRING)
    val date: LocalDate,
    val condition: String,
    val temp: Double?,
    val precipitationProbability: Int?,
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class AiScheduleResponse(
    val tripName: String? = null,
    val weatherSummary: String? = null,
    val dailySchedules: List<AiDailySchedule>? = null,
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class AiDailySchedule(
    val day: Int? = null,
    val date: String? = null,
    val weatherCondition: String? = null,
    val places: List<AiSchedulePlace>? = null,
)

/** placeId는 숫자·문자열 어느 쪽으로 와도 문자열로 받는다. tour_places.id와 맞아야 저장된다. */
@JsonIgnoreProperties(ignoreUnknown = true)
data class AiSchedulePlace(
    val step: Int? = null,
    val placeId: String? = null,
    val placeName: String? = null,
    val startTime: String? = null,
    val endTime: String? = null,
    val reason: String? = null,
)
