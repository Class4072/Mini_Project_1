package com.trip.core.domain.trip

import com.trip.core.domain.BaseTimeEntity
import com.trip.core.domain.schedule.Schedule
import jakarta.persistence.CascadeType
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.OneToMany
import jakarta.persistence.OrderBy
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.Instant
import java.time.LocalDate
import java.time.temporal.ChronoUnit

/** 여행 (DATABASE.md 4.8) */
@Entity
@Table(name = "trips")
class Trip(
    @Column(name = "region_code", nullable = false)
    val regionCode: String,
    @Column(name = "start_date", nullable = false)
    val startDate: LocalDate,
    @Column(name = "end_date", nullable = false)
    val endDate: LocalDate,
    @Enumerated(EnumType.STRING)
    @Column(name = "companion_type", nullable = false)
    val companionType: CompanionType,
    @JdbcTypeCode(SqlTypes.SMALLINT)
    @Column(name = "traveler_count", nullable = false)
    val travelerCount: Int,
    @Enumerated(EnumType.STRING)
    @Column(name = "transport", nullable = false)
    val transport: Transport,
    themes: List<Theme>,
    @Enumerated(EnumType.STRING)
    @Column(name = "places_per_day", nullable = false)
    val placesPerDay: PlacesPerDay,
    @Enumerated(EnumType.STRING)
    @Column(name = "start_time", nullable = false)
    val startTime: StartTimeOption,
    @Column(name = "user_id")
    val userId: Long? = null,
) : BaseTimeEntity() {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0L
        protected set

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "themes", nullable = false)
    private var themeCodes: Array<String> = themes.map { it.name }.toTypedArray()

    val themes: List<Theme>
        get() = themeCodes.map(Theme::valueOf)

    @Column(name = "title")
    var title: String? = null
        protected set

    @Column(name = "weather_summary")
    var weatherSummary: String? = null
        protected set

    @Column(name = "memo")
    var memo: String? = null
        protected set

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    var status: TripStatus = TripStatus.GENERATING
        protected set

    @Column(name = "deleted_at")
    var deletedAt: Instant? = null
        protected set

    @OneToMany(mappedBy = "trip", cascade = [CascadeType.ALL], orphanRemoval = true)
    @OrderBy("dayNumber ASC")
    private val _schedules: MutableList<Schedule> = mutableListOf()

    val schedules: List<Schedule>
        get() = _schedules

    /** 출발일·도착일을 포함한 여행 일수 */
    val dayCount: Int
        get() = ChronoUnit.DAYS.between(startDate, endDate).toInt() + 1

    fun addSchedule(schedule: Schedule) {
        _schedules.add(schedule)
    }

    fun complete(title: String?, weatherSummary: String?) {
        this.title = title
        this.weatherSummary = weatherSummary
        this.status = TripStatus.COMPLETED
    }

    fun fail() {
        this.status = TripStatus.FAILED
    }

    fun updateInfo(title: String, memo: String?) {
        this.title = title
        this.memo = memo
    }

    /** TR-004: 행은 남기고 deleted_at만 채운다 (trips에는 DELETE 권한이 없다) */
    fun delete(now: Instant) {
        this.deletedAt = now
    }
}
