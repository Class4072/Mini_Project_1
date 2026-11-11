package com.trip.core.domain.trip

import org.springframework.data.jpa.repository.JpaRepository

interface TripRepository : JpaRepository<Trip, Long> {
    fun findByIdAndDeletedAtIsNull(id: Long): Trip?
}
