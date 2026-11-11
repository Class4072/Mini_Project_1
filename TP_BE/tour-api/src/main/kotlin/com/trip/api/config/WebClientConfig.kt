package com.trip.api.config

import io.netty.channel.ChannelOption
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.client.reactive.ReactorClientHttpConnector
import org.springframework.web.reactive.function.client.WebClient
import reactor.netty.http.client.HttpClient
import java.time.Duration

/** 외부 서비스 호출용 WebClient (BACKEND.md 1장: 코루틴 + 비동기 WebClient) */
@Configuration
class WebClientConfig {
    @Bean
    fun aiWebClient(builder: WebClient.Builder, properties: AiServiceProperties): WebClient = builder
        .clone()
        .baseUrl(properties.baseUrl)
        // 전체 시간 제한은 AiServiceClient의 withTimeout이 맡고, 여기는 연결이 끊긴 경우를 대비한 안전망
        .clientConnector(connector(AI_CONNECT_TIMEOUT_MILLIS, properties.timeout.plusSeconds(5)))
        .build()

    @Bean
    fun kakaoMobilityWebClient(builder: WebClient.Builder, properties: KakaoMobilityProperties): WebClient = builder
        .clone()
        .baseUrl(properties.baseUrl)
        .clientConnector(connector(KAKAO_CONNECT_TIMEOUT_MILLIS, Duration.ofSeconds(5)))
        .build()

    private fun connector(connectTimeoutMillis: Int, responseTimeout: Duration) = ReactorClientHttpConnector(
        HttpClient
            .create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, connectTimeoutMillis)
            .responseTimeout(responseTimeout),
    )

    companion object {
        private const val AI_CONNECT_TIMEOUT_MILLIS = 5_000
        private const val KAKAO_CONNECT_TIMEOUT_MILLIS = 3_000
    }
}
