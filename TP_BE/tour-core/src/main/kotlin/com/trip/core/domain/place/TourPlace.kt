package com.trip.core.domain.place

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.Table
import org.hibernate.annotations.Immutable

/** 장소 (DATABASE.md 4.2). 배치가 채우고 백엔드는 읽기만 한다. 백엔드가 쓰는 컬럼만 매핑한다. */
@Entity
@Immutable
@Table(name = "tour_places")
class TourPlace(
    @Id
    val id: Long,
    @Column(name = "content_id", nullable = false)
    val contentId: String,
    @Column(name = "name", nullable = false)
    val name: String,
    @Enumerated(EnumType.STRING)
    @Column(name = "category", nullable = false)
    val category: Category,
    @Column(name = "region_code", nullable = false)
    val regionCode: String,
    @Column(name = "address")
    val address: String?,
    @Column(name = "latitude", nullable = false)
    val latitude: Double,
    @Column(name = "longitude", nullable = false)
    val longitude: Double,
    @Column(name = "image_url")
    val imageUrl: String?,
    @Column(name = "is_indoor", nullable = false)
    val indoor: Boolean,
    @Column(name = "is_deleted", nullable = false)
    val deleted: Boolean,
)
