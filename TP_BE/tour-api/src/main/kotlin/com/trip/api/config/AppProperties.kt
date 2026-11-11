package com.trip.api.config

import org.springframework.boot.context.properties.ConfigurationProperties
import java.time.Duration

/** AI 마이크로서비스 (BACKEND.md 10장 ai.service) */
@ConfigurationProperties("ai.service")
data class AiServiceProperties(val baseUrl: String, val timeoutSeconds: Long) {
    val timeout: Duration
        get() = Duration.ofSeconds(timeoutSeconds)
}

/** PLAN-002 공유 링크 주소의 앞부분. 예: https://trp.com/s → https://trp.com/s/{token} */
@ConfigurationProperties("app.share")
data class ShareProperties(val baseUrl: String)

/** MAP-003 길찾기. REST API 키가 없으면 직선거리로 추정한다. */
@ConfigurationProperties("kakao.mobility")
data class KakaoMobilityProperties(val baseUrl: String, val restApiKey: String = "")
