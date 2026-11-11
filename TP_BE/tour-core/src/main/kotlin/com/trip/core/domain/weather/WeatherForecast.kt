package com.trip.core.domain.weather

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.Table
import org.hibernate.annotations.Immutable
import java.time.LocalDate

/** 일자별 날씨 예보 (DATABASE.md 4.6). 배치가 채우고 백엔드는 읽기만 한다. */
@Entity
@Immutable
@Table(name = "weather_forecast")
class WeatherForecast(
    @Id
    val id: Long,
    @Column(name = "region_code", nullable = false)
    val regionCode: String,
    @Column(name = "forecast_date", nullable = false)
    val forecastDate: LocalDate,
    @Enumerated(EnumType.STRING)
    @Column(name = "condition_code", nullable = false)
    val conditionCode: WeatherCondition,
    @Column(name = "temperature")
    val temperature: Double?,
    @Column(name = "precipitation_prob")
    val precipitationProb: Int?,
)
