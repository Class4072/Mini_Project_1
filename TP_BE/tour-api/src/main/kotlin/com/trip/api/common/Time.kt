package com.trip.api.common

import java.time.ZoneId

/** 날짜 판단(출발일 검사 등)과 응답 시각은 한국 시간 기준 */
val KST: ZoneId = ZoneId.of("Asia/Seoul")
