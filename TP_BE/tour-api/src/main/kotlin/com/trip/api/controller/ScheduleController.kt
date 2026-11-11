package com.trip.api.controller

import com.trip.api.common.ApiResponse
import com.trip.api.dto.ScheduleResponse
import com.trip.api.dto.ScheduleSaveRequest
import com.trip.api.dto.ShareCreateRequest
import com.trip.api.dto.ShareCreateResponse
import com.trip.api.service.ExportFile
import com.trip.api.service.ExportService
import com.trip.api.service.ScheduleService
import com.trip.api.service.ShareService
import jakarta.validation.Valid
import org.springframework.http.ContentDisposition
import org.springframework.http.HttpHeaders
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.nio.charset.StandardCharsets

/** 일정 및 내보내기 API (BACKEND.md 3.2) */
@RestController
@RequestMapping("/api/v1/schedules")
class ScheduleController(
    private val scheduleService: ScheduleService,
    private val shareService: ShareService,
    private val exportService: ExportService,
) {
    /** PLAN-001 수동 편집된 일정 저장 */
    @PostMapping
    fun saveSchedule(@Valid @RequestBody request: ScheduleSaveRequest): ApiResponse<ScheduleResponse> =
        ApiResponse.success(scheduleService.saveSchedule(request), "일정이 저장되었습니다.")

    /** PLAN-002 읽기 전용 공유 URL 생성 */
    @PostMapping("/share")
    fun createShare(@Valid @RequestBody request: ShareCreateRequest): ApiResponse<ShareCreateResponse> =
        ApiResponse.success(shareService.createShare(request))

    /** PLAN-003 엑셀 다운로드 (ApiResponse로 감싸지 않고 파일을 그대로 보낸다) */
    @GetMapping("/{id}/export/excel")
    fun exportExcel(@PathVariable id: Long): ResponseEntity<ByteArray> = exportService.exportExcel(id).toResponse()

    /** PLAN-004 PDF 다운로드 */
    @GetMapping("/{id}/export/pdf")
    fun exportPdf(@PathVariable id: Long): ResponseEntity<ByteArray> = exportService.exportPdf(id).toResponse()

    private fun ExportFile.toResponse(): ResponseEntity<ByteArray> = ResponseEntity
        .ok()
        .contentType(mediaType)
        .header(
            HttpHeaders.CONTENT_DISPOSITION,
            ContentDisposition.attachment().filename(fileName, StandardCharsets.UTF_8).build().toString(),
        ).body(bytes)
}
