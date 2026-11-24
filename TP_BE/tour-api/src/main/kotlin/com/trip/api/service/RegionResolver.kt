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
 * 통합된 시도(전남광주)는 옛 시도 코드(광주 "5")를 하위 시군구만 갖고 있어서, 그때는 시군구로 찾아 상위 시도를 쓴다.
 */
@Component
class RegionResolver(private val regionRepository: RegionRepository) {
    fun resolve(code: String): Region {
        val normalized = code.trim().take(MAX_CODE_LENGTH)
        if (normalized.isEmpty()) throw BusinessException(ErrorCode.REGION_NOT_FOUND, "지역 코드를 입력해 주세요.")
        return regionRepository.findByIdOrNull(normalized)
            ?: regionRepository.findFirstByLevelAndTourAreaCode(RegionLevel.SIDO, normalized)
            ?: regionRepository.findFirstByLevelAndTourAreaCode(RegionLevel.SIGUNGU, normalized)
                ?.parentCode
                ?.let { regionRepository.findByIdOrNull(it) }
            ?: throw BusinessException(ErrorCode.REGION_NOT_FOUND, "지원하지 않는 지역 코드입니다: $normalized")
    }

    /**
     * 일정 생성 요청의 지역 코드들을 지역 목록으로 바꾼다. 순서는 요청 순서이고 첫 번째가 대표 지역이다.
     * 한 지역을 코드 여러 개로 보내면(전남광주 = 전남 "38" + 광주 "5") 한 번만 남긴다.
     */
    fun resolveAll(codes: List<String>): List<Region> = codes.map(::resolve).distinctBy { it.regionCode }

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
