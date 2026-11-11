package com.trip.api.service

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.api.dto.TripDetailResponse
import com.trip.core.domain.region.RegionRepository
import com.trip.core.domain.trip.TripRepository
import org.springframework.data.repository.findByIdOrNull
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional

@Service
@Transactional(readOnly = true)
class TripQueryService(private val tripRepository: TripRepository, private val regionRepository: RegionRepository) {
    /**
     * TR-002. 일정·방문 장소·장소 정보는 default_batch_fetch_size(100)로 묶어서 읽는다.
     * (여행 1건 + 일정 + 방문 장소 + 장소, 일정 수와 상관없이 쿼리 몇 번으로 끝남)
     */
    fun getTripDetail(tripId: Long): TripDetailResponse {
        val trip =
            tripRepository.findByIdAndDeletedAtIsNull(tripId) ?: throw BusinessException(ErrorCode.TRIP_NOT_FOUND)
        return TripDetailResponse.of(trip, regionRepository.findByIdOrNull(trip.regionCode))
    }
}
