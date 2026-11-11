package com.trip.api.service

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.dto.DailyScheduleResponse
import com.trip.api.dto.ScheduleResponse
import com.trip.api.dto.ScheduleSaveRequest
import com.trip.core.domain.place.TourPlaceRepository
import com.trip.core.domain.schedule.ScheduleRepository
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional

@Service
class ScheduleService(
    private val scheduleRepository: ScheduleRepository,
    private val tourPlaceRepository: TourPlaceRepository,
) {
    /** PLAN-001 수동 편집 저장: 하루의 방문 장소를 지우고 요청 순서대로 다시 쓴다 (DATABASE.md 6.2) */
    @Transactional
    fun saveSchedule(request: ScheduleSaveRequest): ScheduleResponse {
        val scheduleId = requireNotNull(request.scheduleId)
        val items = requireNotNull(request.places)
        items.forEachIndexed { index, item ->
            val start = item.startTime
            val end = item.endTime
            if (start != null && end != null && end.isBefore(start)) {
                throw BusinessException(ErrorCode.INVALID_REQUEST, "places[$index]: 끝나는 시각이 시작 시각보다 앞입니다.")
            }
        }
        val schedule =
            scheduleRepository.findActiveById(scheduleId) ?: throw BusinessException(ErrorCode.SCHEDULE_NOT_FOUND)

        val placeIds = items.map { requireNotNull(it.placeId) }.toSet()
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
        val missing = placeIds - places.keys
        if (missing.isNotEmpty()) {
            throw BusinessException(ErrorCode.PLACE_NOT_FOUND, "존재하지 않는 장소가 포함되어 있습니다: ${missing.sorted()}")
        }

        schedule.clearPlaces()
        // 기존 행을 먼저 지워야 새 행의 방문 순서가 UNIQUE (schedule_id, visit_order)와 부딪히지 않는다
        scheduleRepository.flush()
        items.forEach { item ->
            schedule.addPlace(
                places.getValue(requireNotNull(item.placeId)),
                item.startTime,
                item.endTime,
                item.reason?.trim()?.ifBlank { null },
            )
        }
        log.info("일정 수정 저장 | scheduleId={}, placesCount={}", scheduleId, items.size)
        return ScheduleResponse(schedule.trip.id, DailyScheduleResponse.of(schedule))
    }

    companion object {
        private val log = LoggerFactory.getLogger(ScheduleService::class.java)
    }
}
