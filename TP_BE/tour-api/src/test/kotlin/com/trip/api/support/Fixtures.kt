package com.trip.api.support

import org.springframework.jdbc.core.JdbcTemplate
import java.time.LocalDate
import java.util.UUID

/** 배치가 채우는 테이블(지역·장소·날씨)에 테스트 데이터를 넣는다 */
class Fixtures(private val jdbc: JdbcTemplate) {
    fun truncateAll() {
        jdbc.execute(
            "TRUNCATE trip_shares, schedule_places, schedules, trips, users, weather_forecast, tour_place_images, " +
                "tour_place_details, tour_embeddings, tour_places, region RESTART IDENTITY CASCADE",
        )
    }

    fun region(
        code: String,
        name: String,
        level: String = "SIDO",
        parent: String? = null,
        tourAreaCode: String? = null,
    ) {
        jdbc.update(
            "INSERT INTO region (region_code, name, level, parent_code, tour_area_code) VALUES (?, ?, ?, ?, ?)",
            code,
            name,
            level,
            parent,
            tourAreaCode,
        )
    }

    fun place(
        name: String,
        regionCode: String,
        category: String = "TOUR_SPOT",
        latitude: Double = 35.1587,
        longitude: Double = 129.1604,
        indoor: Boolean = false,
        deleted: Boolean = false,
        address: String? = null,
    ): Long = requireNotNull(
        jdbc.queryForObject(
            "INSERT INTO tour_places (content_id, content_type_id, name, category, region_code, address, " +
                "latitude, longitude, is_indoor, is_deleted) VALUES (?, '12', ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
            Long::class.java,
            UUID.randomUUID().toString(),
            name,
            category,
            regionCode,
            address,
            latitude,
            longitude,
            indoor,
            deleted,
        ),
    )

    fun weather(
        regionCode: String,
        date: LocalDate,
        condition: String,
        temperature: Double?,
        precipitationProb: Int?,
    ) {
        jdbc.update(
            "INSERT INTO weather_forecast " +
                "(region_code, forecast_date, condition_code, temperature, precipitation_prob, source) " +
                "VALUES (?, ?, ?, ?, ?, 'SHORT')",
            regionCode,
            date,
            condition,
            temperature,
            precipitationProb,
        )
    }

    fun tripStatuses(): List<String> = jdbc.queryForList("SELECT status FROM trips ORDER BY id", String::class.java)

    fun isSoftDeleted(tripId: Long): Boolean =
        jdbc.queryForObject("SELECT deleted_at IS NOT NULL FROM trips WHERE id = ?", Boolean::class.java, tripId) ==
            true

    fun count(table: String): Int = jdbc.queryForObject("SELECT count(*) FROM $table", Int::class.java) ?: 0
}
