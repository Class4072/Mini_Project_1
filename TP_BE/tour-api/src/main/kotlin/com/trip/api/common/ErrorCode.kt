package com.trip.api.common

import org.springframework.http.HttpStatus

enum class ErrorCode(val status: HttpStatus, val message: String) {
    INVALID_REQUEST(HttpStatus.BAD_REQUEST, "요청 값이 올바르지 않습니다."),
    REGION_NOT_FOUND(HttpStatus.BAD_REQUEST, "지원하지 않는 지역 코드입니다."),
    PLACE_NOT_FOUND(HttpStatus.BAD_REQUEST, "존재하지 않는 장소가 포함되어 있습니다."),
    TRIP_NOT_FOUND(HttpStatus.NOT_FOUND, "여행을 찾을 수 없습니다."),
    SCHEDULE_NOT_FOUND(HttpStatus.NOT_FOUND, "일정을 찾을 수 없습니다."),
    SHARE_NOT_FOUND(HttpStatus.NOT_FOUND, "공유 링크를 찾을 수 없습니다."),
    SHARE_EXPIRED(HttpStatus.GONE, "만료된 공유 링크입니다."),
    AI_SERVICE_TIMEOUT(HttpStatus.GATEWAY_TIMEOUT, "일정 만들기가 오래 걸려 멈췄습니다. 잠시 후 다시 시도해 주세요."),
    AI_SERVICE_ERROR(HttpStatus.BAD_GATEWAY, "일정을 만들지 못했습니다. 잠시 후 다시 시도해 주세요."),
    AI_INVALID_RESPONSE(HttpStatus.BAD_GATEWAY, "AI가 만든 일정을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요."),
    EXPORT_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "파일을 만들지 못했습니다."),
}
