package com.trip.api.controller

import com.trip.api.common.ApiResponse
import com.trip.api.dto.CommonResultResponse
import com.trip.api.dto.TripCreateRequest
import com.trip.api.dto.TripDetailResponse
import com.trip.api.dto.TripResponse
import com.trip.api.dto.TripUpdateRequest
import com.trip.api.service.TripCommandService
import com.trip.api.service.TripQueryService
import com.trip.api.service.TripService
import jakarta.validation.Valid
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

/** 여행 관리 API (BACKEND.md 3.1) */
@RestController
@RequestMapping("/api/v1/trips")
class TripController(
    private val tripService: TripService,
    private val tripQueryService: TripQueryService,
    private val tripCommandService: TripCommandService,
) {
    /** TR-001 신규 여행 생성 및 AI 일정 자동 발급. AI 응답을 기다리는 동안 요청 스레드를 놓아준다 (suspend). */
    @PostMapping
    suspend fun createTrip(@Valid @RequestBody request: TripCreateRequest): ApiResponse<TripDetailResponse> =
        ApiResponse.success(tripService.createTripWithAiSchedule(request), "여행 일정이 생성되었습니다.")

    /** TR-002 여행 및 일정 상세 조회 */
    @GetMapping("/{id}")
    fun getTrip(@PathVariable id: Long): ApiResponse<TripDetailResponse> =
        ApiResponse.success(tripQueryService.getTripDetail(id))

    /** TR-003 여행 이름·메모 수정 */
    @PutMapping("/{id}")
    fun updateTrip(@PathVariable id: Long, @Valid @RequestBody request: TripUpdateRequest): ApiResponse<TripResponse> =
        ApiResponse.success(tripCommandService.updateTrip(id, request))

    /** TR-004 여행 삭제 (Soft Delete) */
    @DeleteMapping("/{id}")
    fun deleteTrip(@PathVariable id: Long): ApiResponse<CommonResultResponse> =
        ApiResponse.success(tripCommandService.deleteTrip(id), "여행이 삭제되었습니다.")
}
