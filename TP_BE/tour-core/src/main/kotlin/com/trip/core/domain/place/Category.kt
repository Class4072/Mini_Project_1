package com.trip.core.domain.place

/** 장소 분류 (DATABASE.md 3장 Category) */
enum class Category(val label: String) {
    TOUR_SPOT("관광지"),
    CULTURE("문화시설"),
    FESTIVAL("축제·공연"),
    LEISURE("레포츠"),
    ACCOMMODATION("숙박"),
    SHOPPING("쇼핑"),
    RESTAURANT("음식점"),
    CAFE("카페"),
}
