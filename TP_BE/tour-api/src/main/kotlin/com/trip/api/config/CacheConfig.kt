package com.trip.api.config

import com.fasterxml.jackson.databind.ObjectMapper
import com.trip.api.dto.PlaceMarkerResponse
import org.springframework.boot.autoconfigure.cache.RedisCacheManagerBuilderCustomizer
import org.springframework.cache.annotation.CachingConfigurer
import org.springframework.cache.annotation.EnableCaching
import org.springframework.cache.interceptor.CacheErrorHandler
import org.springframework.cache.interceptor.LoggingCacheErrorHandler
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.data.redis.cache.RedisCacheConfiguration
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer
import org.springframework.data.redis.serializer.RedisSerializationContext
import org.springframework.data.redis.serializer.RedisSerializer
import java.time.Duration

/**
 * Redis 캐시 (BACKEND.md 2장). 장소 데이터는 배치가 하루 단위로 바꾸므로 지도 마커 조회를 잠깐 캐싱한다.
 * Redis 없이 실행하려면 CACHE_TYPE=none.
 */
@Configuration
@EnableCaching
class CacheConfig : CachingConfigurer {
    @Bean
    fun redisCacheCustomizer(objectMapper: ObjectMapper): RedisCacheManagerBuilderCustomizer =
        RedisCacheManagerBuilderCustomizer { builder ->
            builder.withCacheConfiguration(
                PLACE_MARKERS,
                RedisCacheConfiguration
                    .defaultCacheConfig()
                    .prefixCacheNameWith(KEY_PREFIX)
                    .entryTtl(Duration.ofMinutes(10))
                    .disableCachingNullValues()
                    .serializeValuesWith(
                        RedisSerializationContext.SerializationPair.fromSerializer(
                            placeMarkersSerializer(objectMapper),
                        ),
                    ),
            )
        }

    // Redis가 내려가 있어도 캐시 오류는 경고 로그만 남기고 DB 조회로 넘어간다
    override fun errorHandler(): CacheErrorHandler = LoggingCacheErrorHandler()

    companion object {
        const val PLACE_MARKERS = "placeMarkers"
        private const val KEY_PREFIX = "tp:"

        /** 타입 정보를 JSON에 넣지 않고 List<PlaceMarkerResponse>로 고정해 읽고 쓴다 */
        fun placeMarkersSerializer(objectMapper: ObjectMapper): RedisSerializer<Any> = Jackson2JsonRedisSerializer(
            objectMapper,
            objectMapper.typeFactory.constructCollectionType(List::class.java, PlaceMarkerResponse::class.java),
        )
    }
}
