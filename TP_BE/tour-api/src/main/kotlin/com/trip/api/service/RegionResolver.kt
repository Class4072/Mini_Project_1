package com.trip.api.service

import com.trip.api.common.BusinessException
import com.trip.api.common.ErrorCode
import com.trip.core.domain.region.Region
import com.trip.core.domain.region.RegionLevel
import com.trip.core.domain.region.RegionRepository
import org.springframework.data.repository.findByIdOrNull
import org.springframework.stereotype.Component

/**
 * 요청의 지역 코드를 region 행으로 바꾼다 (DATABASE.md 4.8).
 * FE는 TourAPI 지역코드(예: 부산 "6")를 보내므로 region_code가 없으면 시도의 tour_area_code로 찾는다.
 */
@Component
class RegionResolver(private val regionRepository: RegionRepository) {
    fun resolve(code: String): Region {
        val normalized = code.trim().take(MAX_CODE_LENGTH)
        if (normalized.isEmpty()) throw BusinessException(ErrorCode.REGION_NOT_FOUND, "지역 코드를 입력해 주세요.")
        return regionRepository.findByIdOrNull(normalized)
            ?: regionRepository.findFirstByLevelAndTourAreaCode(RegionLevel.SIDO, normalized)
            ?: throw BusinessException(ErrorCode.REGION_NOT_FOUND, "지원하지 않는 지역 코드입니다: $normalized")
    }

    /** 시도를 고르면 하위 시군구까지 포함한다 (DATABASE.md 4.1) */
    fun withChildren(region: Region): List<String> = when (region.level) {
        RegionLevel.SIDO -> listOf(region.regionCode) +
            regionRepository.findAllByParentCode(region.regionCode).map { it.regionCode }
        RegionLevel.SIGUNGU -> listOf(region.regionCode)
    }

    companion object {
        private const val MAX_CODE_LENGTH = 20
    }
}
