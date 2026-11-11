package com.trip.api.controller

import com.trip.api.common.ApiResponse
import com.trip.api.dto.TripDetailResponse
import com.trip.api.service.ShareService
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

/**
 * 공유 링크로 여행 보기. BACKEND.md 3장 표에는 없지만, PLAN-002로 만든 링크를 열려면 필요해서 추가했다.
 * 공유 화면(https://trp.com/s/{token})이 이 API로 데이터를 읽는다.
 */
@RestController
@RequestMapping("/api/v1/shares")
class ShareController(private val shareService: ShareService) {
    @GetMapping("/{token}")
    fun getSharedTrip(@PathVariable token: String): ApiResponse<TripDetailResponse> =
        ApiResponse.success(shareService.getSharedTrip(token))
}
