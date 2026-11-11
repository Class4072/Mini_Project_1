package com.trip.api.client

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.config.AiServiceProperties
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.withTimeout
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.core.codec.CodecException
import org.springframework.stereotype.Component
import org.springframework.web.reactive.function.client.WebClient
import org.springframework.web.reactive.function.client.WebClientException
import org.springframework.web.reactive.function.client.awaitBody
import org.springframework.web.reactive.function.client.bodyToMono

/** AI 서비스 호출 (BACKEND.md 4장 2단계). 실패는 모두 BusinessException(AI_*)으로 바꾼다. */
@Component
class AiServiceClient(
    @param:Qualifier("aiWebClient") private val webClient: WebClient,
    private val properties: AiServiceProperties,
) {
    suspend fun generateSchedule(request: AiScheduleRequest): AiScheduleResponse {
        val startedAt = System.nanoTime()
        return try {
            withTimeout(properties.timeout.toMillis()) {
                webClient
                    .post()
                    .uri(SCHEDULE_PATH)
                    .bodyValue(request)
                    .retrieve()
                    .onStatus({ it.isError }) { response ->
                        response
                            .bodyToMono<String>()
                            .defaultIfEmpty("")
                            .map { body -> AiErrorResponseException(response.statusCode().value(), body) }
                    }.awaitBody<AiScheduleResponse>()
            }.also {
                log.info("AI 일정 생성 응답 수신 | durationMs={}", elapsedMillis(startedAt))
            }
        } catch (e: TimeoutCancellationException) {
            log.error("AI 일정 생성 시간 초과 | timeoutSeconds={}", properties.timeoutSeconds)
            throw BusinessException(ErrorCode.AI_SERVICE_TIMEOUT)
        } catch (e: AiErrorResponseException) {
            log.error("AI 서비스 오류 응답 | status={}, body={}", e.status, e.body.take(LOG_BODY_LIMIT))
            throw BusinessException(ErrorCode.AI_SERVICE_ERROR)
        } catch (e: CodecException) {
            log.error("AI 응답을 읽을 수 없음 | durationMs={}", elapsedMillis(startedAt), e)
            throw BusinessException(ErrorCode.AI_INVALID_RESPONSE)
        } catch (e: WebClientException) {
            log.error("AI 서비스 호출 실패 | durationMs={}", elapsedMillis(startedAt), e)
            throw BusinessException(ErrorCode.AI_SERVICE_ERROR)
        }
    }

    private fun elapsedMillis(startedAt: Long): Long = (System.nanoTime() - startedAt) / 1_000_000

    private class AiErrorResponseException(val status: Int, val body: String) :
        RuntimeException("AI service responded $status")

    companion object {
        const val SCHEDULE_PATH = "/api/v1/ai/schedule"
        private const val LOG_BODY_LIMIT = 500
        private val log = LoggerFactory.getLogger(AiServiceClient::class.java)
    }
}
