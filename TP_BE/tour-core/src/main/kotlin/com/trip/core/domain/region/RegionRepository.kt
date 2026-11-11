package com.trip.core.domain.region

import org.springframework.data.jpa.repository.JpaRepository

interface RegionRepository : JpaRepository<Region, String> {
    fun findFirstByLevelAndTourAreaCode(level: RegionLevel, tourAreaCode: String): Region?

    fun findAllByParentCode(parentCode: String): List<Region>
}
