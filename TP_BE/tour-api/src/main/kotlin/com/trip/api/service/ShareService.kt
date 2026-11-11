package com.trip.api.service

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.config.ShareProperties
import com.trip.api.dto.ShareCreateRequest
import com.trip.api.dto.ShareCreateResponse
import com.trip.api.dto.TripDetailResponse
import com.trip.core.domain.schedule.ScheduleRepository
import com.trip.core.domain.share.TripShare
import com.trip.core.domain.share.TripShareRepository
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.security.SecureRandom
import java.time.Clock
import java.time.Instant
import java.util.Base64

@Service
class ShareService(
    private val scheduleRepository: ScheduleRepository,
    private val tripShareRepository: TripShareRepository,
    private val tripQueryService: TripQueryService,
    private val shareProperties: ShareProperties,
    private val clock: Clock,
) {
    private val random = SecureRandom()

    /**
     * PLAN-002 공유 링크 생성. 요청은 scheduleId(BACKEND.md)지만 trip_shares는 여행 단위라
     * 그 일정이 속한 여행 전체를 공유한다. 이미 만든 링크가 있으면 같은 링크를 돌려준다.
     */
    @Transactional
    fun createShare(request: ShareCreateRequest): ShareCreateResponse {
        val schedule =
            scheduleRepository.findActiveById(requireNotNull(request.scheduleId))
                ?: throw BusinessException(ErrorCode.SCHEDULE_NOT_FOUND)
        val trip = schedule.trip
        val share =
            tripShareRepository.findFirstByTripIdOrderByIdDesc(trip.id)?.takeUnless { it.isExpired(Instant.now(clock)) }
                ?: tripShareRepository.save(TripShare(trip, newToken())).also {
                    log.info("공유 링크 생성 | tripId={}", trip.id)
                }
        return ShareCreateResponse(
            shareUrl = "${shareProperties.baseUrl.trimEnd('/')}/${share.token}",
            token = share.token,
        )
    }

    /** 공유 링크로 여행 보기 (읽기 전용). 메모는 개인 기록이라 공유 화면에서 뺀다. */
    @Transactional(readOnly = true)
    fun getSharedTrip(token: String): TripDetailResponse {
        val share =
            token.takeIf { it.length <= MAX_TOKEN_LENGTH }?.let { tripShareRepository.findByTokenWithTrip(it) }
                ?: throw BusinessException(ErrorCode.SHARE_NOT_FOUND)
        if (share.trip.deletedAt != null) throw BusinessException(ErrorCode.SHARE_NOT_FOUND)
        if (share.isExpired(Instant.now(clock))) throw BusinessException(ErrorCode.SHARE_EXPIRED)
        val detail = tripQueryService.getTripDetail(share.trip.id)
        return detail.copy(trip = detail.trip.copy(memo = null))
    }

    // 32바이트 난수 → URL에 그대로 쓸 수 있는 43자
    private fun newToken(): String = ByteArray(TOKEN_BYTES)
        .also(random::nextBytes)
        .let { Base64.getUrlEncoder().withoutPadding().encodeToString(it) }

    companion object {
        private const val TOKEN_BYTES = 32
        private const val MAX_TOKEN_LENGTH = 64
        private val log = LoggerFactory.getLogger(ShareService::class.java)
    }
}
