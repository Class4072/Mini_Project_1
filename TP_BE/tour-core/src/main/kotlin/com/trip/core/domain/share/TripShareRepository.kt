package com.trip.core.domain.share

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query

interface TripShareRepository : JpaRepository<TripShare, Long> {
    @Query("select s from TripShare s join fetch s.trip where s.token = :token")
    fun findByTokenWithTrip(token: String): TripShare?

    fun findFirstByTripIdOrderByIdDesc(tripId: Long): TripShare?
}
