package com.trip.core.domain.schedule

import com.trip.core.domain.place.TourPlace
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.FetchType
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.LocalTime

/** 일정의 방문 장소 (DATABASE.md 4.10). 체류 시간은 end_time - start_time 으로 계산한다. */
@Entity
@Table(name = "schedule_places")
class SchedulePlace(
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "schedule_id", nullable = false)
    val schedule: Schedule,
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "place_id", nullable = false)
    val place: TourPlace,
    @JdbcTypeCode(SqlTypes.SMALLINT)
    @Column(name = "visit_order", nullable = false)
    val visitOrder: Int,
    @Column(name = "start_time")
    val startTime: LocalTime?,
    @Column(name = "end_time")
    val endTime: LocalTime?,
    @Column(name = "reason")
    val reason: String?,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0L
        protected set
}
