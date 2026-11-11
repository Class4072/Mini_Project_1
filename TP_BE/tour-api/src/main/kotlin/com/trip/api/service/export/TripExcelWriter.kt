package com.trip.api.service.export

import com.trip.api.dto.TripDetailResponse
import org.apache.poi.ss.usermodel.CellStyle
import org.apache.poi.ss.usermodel.FillPatternType
import org.apache.poi.ss.usermodel.IndexedColors
import org.apache.poi.ss.usermodel.Row
import org.apache.poi.xssf.usermodel.XSSFWorkbook
import org.springframework.stereotype.Component
import java.io.ByteArrayOutputStream

/** PLAN-003 여행 일정 엑셀 (.xlsx) */
@Component
class TripExcelWriter {
    fun write(detail: TripDetailResponse): ByteArray = XSSFWorkbook().use { workbook ->
        val sheet = workbook.createSheet("여행 일정")
        val titleStyle = workbook.createCellStyle().apply {
            setFont(
                workbook.createFont().apply {
                    bold = true
                    fontHeightInPoints =
                        14
                },
            )
        }
        val headerStyle =
            workbook.createCellStyle().apply {
                setFont(workbook.createFont().apply { bold = true })
                fillForegroundColor = IndexedColors.GREY_25_PERCENT.index
                setFillPattern(FillPatternType.SOLID_FOREGROUND)
            }
        val wrapStyle = workbook.createCellStyle().apply { wrapText = true }

        val introLines =
            listOfNotNull(detail.summaryLine(), detail.trip.weatherSummary, detail.trip.memo?.let { "메모: $it" })
        sheet.createRow(0).writeCells(listOf(detail.displayTitle()), titleStyle)
        introLines.forEachIndexed { index, line -> sheet.createRow(index + 1).writeCells(listOf(line)) }

        val headerRowIndex = introLines.size + 2
        sheet.createRow(headerRowIndex).writeCells(HEADERS, headerStyle)
        val rows =
            detail.dailySchedules.flatMap { day ->
                val dayCells = listOf(day.dayNumber, day.date.toString(), day.weatherLabel())
                if (day.places.isEmpty()) {
                    listOf(dayCells + listOf("", "", "", "", "방문 장소 없음"))
                } else {
                    day.places.map { place ->
                        dayCells +
                            listOf(
                                place.step,
                                place.startTime?.toString().orEmpty(),
                                place.endTime?.toString().orEmpty(),
                                place.stayTimeMinutes ?: "",
                                place.placeName,
                                place.category.label,
                                if (place.isIndoor) "실내" else "실외",
                                place.address.orEmpty(),
                                place.reason.orEmpty(),
                            )
                    }
                }
            }
        rows.forEachIndexed { index, cells ->
            sheet.createRow(headerRowIndex + 1 + index).writeCells(cells, wrapStyle)
        }

        COLUMN_WIDTHS.forEachIndexed { index, width -> sheet.setColumnWidth(index, width * CHARACTER_WIDTH) }
        sheet.createFreezePane(0, headerRowIndex + 1)
        ByteArrayOutputStream().also(workbook::write).toByteArray()
    }

    private fun Row.writeCells(values: List<Any>, style: CellStyle? = null) {
        values.forEachIndexed { index, value ->
            val cell = createCell(index)
            when (value) {
                is Number -> cell.setCellValue(value.toDouble())
                else -> cell.setCellValue(value.toString())
            }
            style?.let { cell.cellStyle = it }
        }
    }

    companion object {
        private val HEADERS = listOf("일차", "날짜", "날씨", "순서", "시작", "종료", "체류(분)", "장소", "분류", "실내외", "주소", "추천 이유")
        private val COLUMN_WIDTHS = listOf(6, 12, 18, 6, 8, 8, 9, 28, 10, 8, 36, 60)
        private const val CHARACTER_WIDTH = 256
    }
}
