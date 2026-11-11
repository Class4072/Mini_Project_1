package com.trip.api.common

import com.fasterxml.jackson.databind.JsonMappingException
import org.slf4j.LoggerFactory
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpStatus
import org.springframework.http.HttpStatusCode
import org.springframework.http.ResponseEntity
import org.springframework.http.converter.HttpMessageNotReadableException
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.context.request.ServletWebRequest
import org.springframework.web.context.request.WebRequest
import org.springframework.web.method.annotation.HandlerMethodValidationException
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler

/**
 * 전역 예외 처리 (BACKEND.md 5.2). 모든 오류를 ApiResponse 형태로 바꾼다.
 * Spring MVC 표준 예외(400·404·405 등)는 ResponseEntityExceptionHandler가 상태 코드를 정하고,
 * handleExceptionInternal 에서 응답 본문만 ApiResponse로 바꾼다.
 */
@RestControllerAdvice
class GlobalExceptionHandler : ResponseEntityExceptionHandler() {
    @ExceptionHandler(BusinessException::class)
    fun handleBusinessException(e: BusinessException): ResponseEntity<ApiResponse<Unit>> {
        log.warn("비즈니스 예외 발생: code={}, message={}", e.errorCode.name, e.message)
        return ResponseEntity
            .status(e.errorCode.status)
            .body(ApiResponse.error(e.errorCode.name, e.message))
    }

    @ExceptionHandler(Exception::class)
    fun handleInternalError(e: Exception): ResponseEntity<ApiResponse<Unit>> {
        log.error("처리되지 않은 서버 내부 오류: ", e)
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ApiResponse.error("INTERNAL_SERVER_ERROR", "서버 내부 오류가 발생했습니다."))
    }

    // 요청 본문 검증 실패 (@Valid)
    override fun handleMethodArgumentNotValid(
        ex: MethodArgumentNotValidException,
        headers: HttpHeaders,
        status: HttpStatusCode,
        request: WebRequest,
    ): ResponseEntity<Any>? {
        val message = ex.bindingResult.fieldErrors.joinToString(", ") { "${it.field}: ${it.defaultMessage}" }
        return handleExceptionInternal(ex, invalidRequest(message), headers, status, request)
    }

    // 쿼리 파라미터 검증 실패 (@Min, @NotBlank 등)
    override fun handleHandlerMethodValidationException(
        ex: HandlerMethodValidationException,
        headers: HttpHeaders,
        status: HttpStatusCode,
        request: WebRequest,
    ): ResponseEntity<Any>? {
        val message =
            ex.parameterValidationResults.joinToString(", ") { result ->
                val name = result.methodParameter.parameterName ?: "parameter"
                result.resolvableErrors.joinToString(", ") { "$name: ${it.defaultMessage}" }
            }
        return handleExceptionInternal(ex, invalidRequest(message), headers, status, request)
    }

    // JSON 문법 오류, 모르는 코드값, 날짜 형식 오류
    override fun handleHttpMessageNotReadable(
        ex: HttpMessageNotReadableException,
        headers: HttpHeaders,
        status: HttpStatusCode,
        request: WebRequest,
    ): ResponseEntity<Any>? {
        val field =
            (ex.cause as? JsonMappingException)
                ?.path
                ?.joinToString(".") { it.fieldName ?: "[${it.index}]" }
        val message =
            if (field.isNullOrBlank()) {
                "요청 본문을 읽을 수 없습니다. JSON 형식을 확인해 주세요."
            } else {
                "$field: 값의 형식이나 코드값이 올바르지 않습니다."
            }
        return handleExceptionInternal(ex, invalidRequest(message), headers, status, request)
    }

    override fun handleExceptionInternal(
        ex: Exception,
        body: Any?,
        headers: HttpHeaders,
        statusCode: HttpStatusCode,
        request: WebRequest,
    ): ResponseEntity<Any>? {
        if ((request as? ServletWebRequest)?.response?.isCommitted == true) {
            log.warn("응답이 이미 전송되어 오류 응답을 보낼 수 없습니다: {}", ex.message)
            return null
        }
        val apiBody = body as? ApiResponse<*> ?: ApiResponse.error(codeOf(statusCode), messageOf(statusCode))
        if (statusCode.is5xxServerError) {
            log.error("요청 처리 실패: status={}, code={}", statusCode.value(), apiBody.code, ex)
        } else {
            log.warn("요청 처리 실패: status={}, code={}, message={}", statusCode.value(), apiBody.code, apiBody.message)
        }
        return ResponseEntity(apiBody, headers, statusCode)
    }

    private fun invalidRequest(message: String): ApiResponse<Unit> =
        ApiResponse.error(ErrorCode.INVALID_REQUEST.name, message.ifBlank { ErrorCode.INVALID_REQUEST.message })

    private fun codeOf(status: HttpStatusCode): String = when (status.value()) {
        400 -> ErrorCode.INVALID_REQUEST.name
        else -> HttpStatus.resolve(status.value())?.name ?: "HTTP_${status.value()}"
    }

    private fun messageOf(status: HttpStatusCode): String = when (status.value()) {
        400 -> ErrorCode.INVALID_REQUEST.message
        404 -> "요청한 주소를 찾을 수 없습니다."
        405 -> "지원하지 않는 HTTP 메서드입니다."
        406, 415 -> "지원하지 않는 형식입니다."
        503 -> "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        else -> "요청을 처리하지 못했습니다."
    }

    companion object {
        private val log = LoggerFactory.getLogger(GlobalExceptionHandler::class.java)
    }
}
