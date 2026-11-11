package com.trip.api.service

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.dto.TripDetailResponse
import com.trip.api.service.export.TripExcelWriter
import com.trip.api.service.export.TripPdfWriter
import com.trip.core.domain.schedule.ScheduleRepository
import org.slf4j.LoggerFactory
import org.springframework.http.MediaType
import org.springframework.stereotype.Service

/**
 * PLAN-003·004 일정 파일 내보내기. 경로는 scheduleId(BACKEND.md)를 받지만,
 * 화면의 [엑셀 다운로드]는 여행 전체를 받는 버튼이라 그 일정이 속한 여행의 모든 일차를 담는다.
 */
@Service
class ExportService(
    private val scheduleRepository: ScheduleRepository,
    private val tripQueryService: TripQueryService,
    private val excelWriter: TripExcelWriter,
    private val pdfWriter: TripPdfWriter,
) {
    fun exportExcel(scheduleId: Long): ExportFile = export(scheduleId, "xlsx", XLSX, excelWriter::write)

    fun exportPdf(scheduleId: Long): ExportFile = export(scheduleId, "pdf", MediaType.APPLICATION_PDF, pdfWriter::write)

    private fun export(
        scheduleId: Long,
        extension: String,
        mediaType: MediaType,
        writer: (TripDetailResponse) -> ByteArray,
    ): ExportFile {
        val tripId =
            scheduleRepository.findActiveById(scheduleId)?.trip?.id
                ?: throw BusinessException(ErrorCode.SCHEDULE_NOT_FOUND)
        val detail = tripQueryService.getTripDetail(tripId)
        val bytes =
            try {
                writer(detail)
            } catch (e: Exception) {
                log.error("일정 파일 생성 실패 | tripId={}, format={}", tripId, extension, e)
                throw BusinessException(ErrorCode.EXPORT_FAILED)
            }
        log.info("일정 파일 생성 | tripId={}, format={}, bytes={}", tripId, extension, bytes.size)
        return ExportFile(fileName(detail, extension), mediaType, bytes)
    }

    private fun fileName(detail: TripDetailResponse, extension: String): String {
        val title = (detail.trip.title ?: "${detail.trip.regionName ?: "여행"} 일정").replace(
            UNSAFE_FILE_CHARS,
            "_",
        ).take(80)
        return "${title}_${detail.trip.startDate}.$extension"
    }

    companion object {
        private val XLSX = MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        private val UNSAFE_FILE_CHARS = Regex("""[\\/:*?"<>|\r\n]""")
        private val log = LoggerFactory.getLogger(ExportService::class.java)
    }
}

class ExportFile(val fileName: String, val mediaType: MediaType, val bytes: ByteArray)
