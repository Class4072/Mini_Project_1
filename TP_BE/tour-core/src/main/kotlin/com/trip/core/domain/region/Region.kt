package com.trip.core.domain.region

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.Table
import org.hibernate.annotations.Immutable

/** 지역 마스터 (DATABASE.md 4.1). 배치가 채우고 백엔드는 읽기만 한다. */
@Entity
@Immutable
@Table(name = "region")
class Region(
    @Id
    @Column(name = "region_code")
    val regionCode: String,
    @Column(name = "name", nullable = false)
    val name: String,
    @Enumerated(EnumType.STRING)
    @Column(name = "level", nullable = false)
    val level: RegionLevel,
    @Column(name = "parent_code")
    val parentCode: String?,
    @Column(name = "tour_area_code")
    val tourAreaCode: String?,
)
