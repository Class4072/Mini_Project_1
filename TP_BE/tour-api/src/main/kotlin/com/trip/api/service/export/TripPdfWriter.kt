package com.trip.api.service.export

import com.lowagie.text.Document
import com.lowagie.text.Element
import com.lowagie.text.Font
import com.lowagie.text.PageSize
import com.lowagie.text.Paragraph
import com.lowagie.text.Phrase
import com.lowagie.text.pdf.BaseFont
import com.lowagie.text.pdf.PdfPCell
import com.lowagie.text.pdf.PdfPTable
import com.lowagie.text.pdf.PdfWriter
import com.trip.api.dto.DailyScheduleResponse
import com.trip.api.dto.TripDetailResponse
import org.springframework.core.io.ClassPathResource
import org.springframework.stereotype.Component
import java.awt.Color
import java.io.ByteArrayOutputStream

/**
 * PLAN-004 여행 일정 PDF.
 * 한글을 쓰려면 폰트를 PDF에 넣어야 해서 나눔고딕(SIL OFL 1.1, fonts/OFL.txt)을 함께 배포한다.
 */
@Component
class TripPdfWriter {
    private val baseFont: BaseFont by lazy {
        val bytes = ClassPathResource(FONT_PATH).inputStream.use { it.readBytes() }
        BaseFont.createFont(FONT_NAME, BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, bytes, null)
    }

    fun write(detail: TripDetailResponse): ByteArray {
        val output = ByteArrayOutputStream()
        val document = Document(PageSize.A4.rotate(), MARGIN, MARGIN, MARGIN, MARGIN)
        PdfWriter.getInstance(document, output)
        document.open()
        try {
            document.add(Paragraph(detail.displayTitle(), font(18f, Font.BOLD)))
            document.add(Paragraph(detail.summaryLine(), font(10f)).apply { spacingBefore = 4f })
            detail.trip.weatherSummary?.let { document.add(Paragraph(it, font(10f))) }
            detail.dailySchedules.forEach { day ->
                document.add(
                    Paragraph("${day.dayLabel()} · ${day.weatherLabel()}", font(13f, Font.BOLD)).apply {
                        spacingBefore = 14f
                        spacingAfter = 6f
                    },
                )
                if (day.places.isEmpty()) {
                    document.add(Paragraph("방문 장소가 없습니다.", font(10f)))
                } else {
                    document.add(placesTable(day))
                }
            }
        } finally {
            document.close()
        }
        return output.toByteArray()
    }

    private fun placesTable(day: DailyScheduleResponse): PdfPTable = PdfPTable(COLUMN_WIDTHS).apply {
        widthPercentage = 100f
        headerRows = 1
        listOf("순서", "시간", "장소", "분류", "추천 이유").forEach { addCell(cell(it, font(9f, Font.BOLD), HEADER_COLOR)) }
        day.places.forEach { place ->
            val name = listOfNotNull(place.placeName, place.address).joinToString("\n")
            val category = "${place.category.label}\n${if (place.isIndoor) "실내" else "실외"}"
            listOf(place.step.toString(), place.timeLabel(), name, category, place.reason.orEmpty())
                .forEach { addCell(cell(it, font(9f))) }
        }
    }

    private fun cell(text: String, font: Font, background: Color? = null): PdfPCell =
        PdfPCell(Phrase(text, font)).apply {
            setPadding(5f)
            verticalAlignment = Element.ALIGN_MIDDLE
            background?.let { backgroundColor = it }
        }

    private fun font(size: Float, style: Int = Font.NORMAL): Font = Font(baseFont, size, style)

    companion object {
        private const val FONT_PATH = "fonts/NanumGothic-Regular.ttf"
        private const val FONT_NAME = "NanumGothic-Regular.ttf"
        private const val MARGIN = 36f
        private val COLUMN_WIDTHS = floatArrayOf(0.6f, 1.4f, 3.2f, 1.1f, 5.7f)
        private val HEADER_COLOR = Color(0xE5, 0xE7, 0xEB)
    }
}
