package com.trip.core.domain.weather

/** 날씨 (DATABASE.md 3장 WeatherCondition) */
enum class WeatherCondition(val label: String) {
    SUNNY("맑음"),
    CLOUDY("흐림"),
    RAIN("비"),
    SNOW("눈"),
    ;

    companion object {
        /** AI 응답처럼 바깥에서 온 문자열을 바꾼다. 모르는 값이면 null */
        fun fromCode(code: String?): WeatherCondition? =
            entries.firstOrNull { it.name.equals(code?.trim(), ignoreCase = true) }
    }
}
