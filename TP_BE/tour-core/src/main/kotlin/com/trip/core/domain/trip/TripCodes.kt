package com.trip.core.domain.trip

import java.time.LocalTime

// 일정 생성 요청의 코드값 (DATABASE.md 3장. FE·AI 일정 생성 요청 초안과 같은 값)

enum class CompanionType(val label: String) {
    SOLO("혼자"),
    COUPLE("연인·부부"),
    FRIENDS("친구"),
    FAMILY_WITH_KIDS("아이와 함께"),
    FAMILY_WITH_PARENTS("부모님과 함께"),
    GROUP("단체"),
}

enum class Transport(val label: String) {
    CAR("자동차"),
    PUBLIC_TRANSIT("대중교통"),
    WALK("도보 위주"),
}

enum class Theme(val label: String) {
    NATURE("자연·풍경"),
    HISTORY_CULTURE("역사·문화"),
    FOOD("맛집"),
    CAFE("카페"),
    ACTIVITY("체험·액티비티"),
    SHOPPING("쇼핑"),
    FESTIVAL("축제·공연"),
    HEALING("휴식·힐링"),
}

enum class PlacesPerDay(val label: String) {
    RELAXED("여유롭게"),
    NORMAL("적당히"),
    PACKED("알차게"),
}

enum class StartTimeOption(val label: String, val time: LocalTime) {
    EARLY("아침 일찍", LocalTime.of(8, 0)),
    NORMAL("보통", LocalTime.of(10, 0)),
    LATE("느긋하게", LocalTime.of(11, 0)),
}

enum class TripStatus {
    GENERATING,
    COMPLETED,
    FAILED,
}
