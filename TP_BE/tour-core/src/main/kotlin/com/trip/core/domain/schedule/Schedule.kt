package com.trip.core.domain.schedule

import com.trip.core.domain.place.TourPlace
import com.trip.core.domain.trip.Trip
import com.trip.core.domain.weather.WeatherCondition
import jakarta.persistence.CascadeType
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.FetchType
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.OneToMany
import jakarta.persistence.OrderBy
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.LocalDate
import java.time.LocalTime

/**
 * 일자별 일정 (DATABASE.md 4.9).
 * 날씨는 일정을 만든 시점의 값을 복사해 둔다 (AI가 어떤 날씨를 보고 짰는지 남기기 위해).
 */
@Entity
@Table(name = "schedules")
class Schedule(
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "trip_id", nullable = false)
    val trip: Trip,
    @JdbcTypeCode(SqlTypes.SMALLINT)
    @Column(name = "day_number", nullable = false)
    val dayNumber: Int,
    @Column(name = "schedule_date", nullable = false)
    val scheduleDate: LocalDate,
    @Enumerated(EnumType.STRING)
    @Column(name = "weather_condition")
    val weatherCondition: WeatherCondition?,
    @Column(name = "temperature")
    val temperature: Double?,
    @Column(name = "precipitation_prob")
    val precipitationProb: Int?,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0L
        protected set

    @OneToMany(mappedBy = "schedule", cascade = [CascadeType.ALL], orphanRemoval = true)
    @OrderBy("visitOrder ASC")
    private val _places: MutableList<SchedulePlace> = mutableListOf()

    val places: List<SchedulePlace>
        get() = _places

    /** 방문 순서(visit_order)는 넣은 순서대로 1부터 매긴다 */
    fun addPlace(place: TourPlace, startTime: LocalTime?, endTime: LocalTime?, reason: String?) {
        _places.add(SchedulePlace(this, place, _places.size + 1, startTime, endTime, reason))
    }

    fun clearPlaces() {
        _places.clear()
    }
}
