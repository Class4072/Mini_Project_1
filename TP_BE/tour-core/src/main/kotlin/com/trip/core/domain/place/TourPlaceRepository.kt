package com.trip.core.domain.place

import org.springframework.data.jpa.repository.JpaRepository

interface TourPlaceRepository :
    JpaRepository<TourPlace, Long>,
    TourPlaceQueryRepository {
    fun findAllByIdInAndDeletedFalse(ids: Collection<Long>): List<TourPlace>
}
