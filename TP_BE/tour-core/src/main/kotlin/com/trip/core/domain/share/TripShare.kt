package com.trip.core.domain.share

import com.trip.core.domain.trip.Trip
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.FetchType
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.Table
import org.hibernate.annotations.CreationTimestamp
import java.time.Instant

/** 읽기 전용 공유 링크 (DATABASE.md 4.11). 여행 전체 단위로 공유한다 (팀 합의 4번 제안). */
@Entity
@Table(name = "trip_shares")
class TripShare(
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "trip_id", nullable = false)
    val trip: Trip,
    @Column(name = "token", nullable = false)
    val token: String,
    @Column(name = "expires_at")
    val expiresAt: Instant? = null,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0L
        protected set

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    lateinit var createdAt: Instant
        protected set

    fun isExpired(now: Instant): Boolean = expiresAt?.let { !it.isAfter(now) } ?: false
}
