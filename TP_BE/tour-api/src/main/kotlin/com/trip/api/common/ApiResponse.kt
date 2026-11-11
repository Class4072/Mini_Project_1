package com.trip.api.common

import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

/** 공통 응답 래퍼 (BACKEND.md 5.1) */
data class ApiResponse<T>(
    val success: Boolean,
    val code: String,
    val message: String,
    val data: T? = null,
    val timestamp: String = LocalDateTime.now(KST).format(DateTimeFormatter.ISO_DATE_TIME),
) {
    companion object {
        fun <T> success(data: T, message: String = "요청이 성공적으로 처리되었습니다."): ApiResponse<T> =
            ApiResponse(success = true, code = "SUCCESS", message = message, data = data)

        fun error(code: String, message: String): ApiResponse<Unit> =
            ApiResponse(success = false, code = code, message = message, data = null)
    }
}
