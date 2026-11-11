package com.trip.core.domain.weather

import org.springframework.data.jpa.repository.JpaRepository
import java.time.LocalDate

interface WeatherForecastRepository : JpaRepository<WeatherForecast, Long> {
    /** DATABASE.md 5.3: 여행 기간 날씨. 행이 없는 날짜는 빠진다. */
    fun findAllByRegionCodeAndForecastDateBetweenOrderByForecastDateAsc(
        regionCode: String,
        from: LocalDate,
        to: LocalDate,
    ): List<WeatherForecast>
}
