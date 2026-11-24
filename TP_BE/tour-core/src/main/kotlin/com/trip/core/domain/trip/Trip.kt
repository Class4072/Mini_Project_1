package com.trip.core.domain.trip

import com.trip.core.domain.BaseTimeEntity
import com.trip.core.domain.schedule.Schedule
import jakarta.persistence.CascadeType
import jakarta.persistence.CollectionTable
import jakarta.persistence.Column
import jakarta.persistence.ElementCollection
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.OneToMany
import jakarta.persistence.OrderBy
import jakarta.persistence.OrderColumn
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.Instant
import java.time.LocalDate
import java.time.temporal.ChronoUnit

/** 여행 (DATABASE.md 4.8). 지역은 여러 개일 수 있고 첫 지역이 대표 지역이다 (4.14). */
@Entity
@Table(name = "trips")
class Trip(
    regionCodes: List<String>,
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

    init {
        require(regionCodes.isNotEmpty()) { "여행 지역이 없습니다." }
    }

    /** 대표 지역 (요청의 첫 지역) */
    @Column(name = "region_code", nullable = false)
    val regionCode: String = regionCodes.first()

    // trip_regions. 여행을 만들 때 같이 넣고 바꾸지 않는다 (tp_backend는 INSERT만 가능)
    @ElementCollection
    @CollectionTable(name = "trip_regions", joinColumns = [JoinColumn(name = "trip_id")])
    @OrderColumn(name = "sort_order")
    @Column(name = "region_code", nullable = false)
    private val regionCodeList: MutableList<String> = regionCodes.toMutableList()

    /** 고른 지역 전부 (첫 번째가 대표 지역) */
    val regionCodes: List<String>
        get() = regionCodeList.ifEmpty { listOf(regionCode) }

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
