package com.trip.api.dto

import com.fasterxml.jackson.annotation.JsonUnwrapped
import jakarta.validation.Valid
import jakarta.validation.constraints.NotNull
import jakarta.validation.constraints.Size
import java.time.LocalTime

/** PLAN-001 하루 일정의 방문 장소를 통째로 바꾼다. 목록 순서가 방문 순서가 된다. */
data class ScheduleSaveRequest(
    @field:NotNull(message = "일정 ID가 필요합니다.")
    val scheduleId: Long? = null,
    @field:NotNull(message = "방문 장소 목록이 필요합니다. 비우려면 빈 배열을 보내 주세요.")
    @field:Size(max = 20, message = "하루 방문 장소는 최대 20곳까지 저장할 수 있습니다.")
    @field:Valid
    val places: List<SchedulePlaceRequest>? = null,
)

data class SchedulePlaceRequest(
    @field:NotNull(message = "장소 ID가 필요합니다.")
    val placeId: Long? = null,
    val startTime: LocalTime? = null,
    val endTime: LocalTime? = null,
    @field:Size(max = 500, message = "추천 이유는 500자 이하로 입력해 주세요.")
    val reason: String? = null,
)

data class ScheduleResponse(
    val tripId: Long,
    @get:JsonUnwrapped
    val schedule: DailyScheduleResponse,
)

/** PLAN-002 공유 링크 생성. 링크는 이 일정이 속한 여행 전체를 보여준다 (DATABASE.md 팀 합의 4번 제안). */
data class ShareCreateRequest(
    @field:NotNull(message = "일정 ID가 필요합니다.")
    val scheduleId: Long? = null,
)

data class ShareCreateResponse(val shareUrl: String, val token: String)
