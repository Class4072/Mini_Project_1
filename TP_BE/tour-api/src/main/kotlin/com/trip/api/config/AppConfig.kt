package com.trip.api.config

import com.fasterxml.jackson.datatype.jsr310.ser.LocalTimeSerializer
import com.trip.api.common.KST
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import java.time.Clock
import java.time.format.DateTimeFormatter

@Configuration
class AppConfig {
    @Bean
    fun clock(): Clock = Clock.system(KST)

    // 응답의 시각은 AI 응답과 같은 "HH:mm" 형식으로 (요청은 "10:30", "10:30:00" 둘 다 받는다)
    @Bean
    fun localTimeFormatCustomizer(): Jackson2ObjectMapperBuilderCustomizer =
        Jackson2ObjectMapperBuilderCustomizer { builder ->
            builder.serializers(LocalTimeSerializer(DateTimeFormatter.ofPattern("HH:mm")))
        }
}
