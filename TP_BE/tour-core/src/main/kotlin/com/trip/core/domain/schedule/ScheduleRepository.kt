package com.trip.core.domain.schedule

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query

interface ScheduleRepository : JpaRepository<Schedule, Long> {
    /** 삭제되지 않은 여행의 일정만 */
    @Query("select s from Schedule s join fetch s.trip t where s.id = :id and t.deletedAt is null")
    fun findActiveById(id: Long): Schedule?

    @Query(
        "select s from Schedule s join fetch s.trip t " +
            "where t.id = :tripId and s.dayNumber = :dayNumber and t.deletedAt is null",
    )
    fun findActiveByTripIdAndDayNumber(tripId: Long, dayNumber: Int): Schedule?
}
