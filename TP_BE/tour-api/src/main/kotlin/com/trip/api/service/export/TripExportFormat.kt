package com.trip.api.service.export

import com.trip.api.dto.DailyScheduleResponse
import com.trip.api.dto.SchedulePlaceResponse
import com.trip.api.dto.TripDetailResponse
import java.time.format.TextStyle
import java.util.Locale

// 엑셀·PDF가 같이 쓰는 표시 문구

internal fun TripDetailResponse.displayTitle(): String = trip.title ?: "${trip.regionName ?: "여행"} 일정"

internal fun TripDetailResponse.summaryLine(): String = listOfNotNull(
    trip.regionName?.let { "지역 $it" },
    "기간 ${trip.startDate} ~ ${trip.endDate}",
    "동행 ${trip.companionType.label} ${trip.travelerCount}명",
    "이동 ${trip.transport.label}",
    trip.themes.takeIf { it.isNotEmpty() }?.joinToString(", ", prefix = "취향 ") { it.label },
).joinToString(" | ")

internal fun DailyScheduleResponse.dayLabel(): String =
    "${dayNumber}일차 · $date (${date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.KOREAN)})"

internal fun DailyScheduleResponse.weatherLabel(): String = listOfNotNull(
    weatherCondition?.label,
    // 번들 폰트(나눔고딕)에 ℃ 글자가 없어 °C로 쓴다
    temperature?.let { "%.0f°C".format(Locale.ROOT, it) },
    precipitationProbability?.let { "강수 $it%" },
).joinToString(" ").ifBlank { "예보 없음" }

internal fun SchedulePlaceResponse.timeLabel(): String = when {
    startTime != null && endTime != null -> "$startTime ~ $endTime"
    startTime != null -> "$startTime ~"
    else -> ""
}
