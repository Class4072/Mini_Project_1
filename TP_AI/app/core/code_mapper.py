from typing import List, Dict, Tuple, Optional, Any


class CodeMapper:
    """02_요청 데이터 명세 초안.md 코드값 매핑 및 유틸리티"""

    # 1. 지역 코드 (TourAPI 지역코드 <-> 한글 지역명)
    REGION_MAP: Dict[str, str] = {
        "1": "서울",
        "2": "인천",
        "3": "대전",
        "4": "대구",
        "5": "광주",
        "6": "부산",
        "7": "울산",
        "8": "세종",
        "31": "경기도",
        "32": "강원도",
        "33": "충청북도",
        "34": "충청남도",
        "35": "경상북도",
        "36": "경상남도",
        "37": "전라북도",
        "38": "전라남도",
        "39": "제주",
    }

    # 영문/한글 별칭 지원
    REGION_ALIAS_MAP: Dict[str, str] = {
        "SEOUL": "서울",
        "BUSAN": "부산",
        "PUSAN": "부산",
        "JEJU": "제주",
        "GANGNEUNG": "강릉",
        "GANGWON": "강원도",
        "INCHEON": "인천",
        "DAEGU": "대구",
        "DAEJEON": "대전",
        "GWANGJU": "광주",
    }

    # 2. 동행 코드 (companionType)
    COMPANION_MAP: Dict[str, Dict[str, Any]] = {
        "SOLO": {"name": "혼자", "tags": ["혼자", "1인"]},
        "COUPLE": {"name": "연인·부부", "tags": ["커플", "데이트"]},
        "FRIENDS": {"name": "친구", "tags": ["친구"]},
        "FAMILY_WITH_KIDS": {"name": "아이와 함께", "tags": ["가족", "키즈", "어린이"]},
        "FAMILY_WITH_PARENTS": {"name": "부모님과 함께", "tags": ["가족", "부모님", "효도"]},
        "GROUP": {"name": "단체", "tags": ["단체", "모임"]},
    }

    # 3. 이동 수단 (transport)
    TRANSPORT_MAP: Dict[str, str] = {
        "CAR": "자동차 자가용 (주차 편의 고려)",
        "PUBLIC_TRANSIT": "대중교통 (지하철/버스 정류장 접근성 고려)",
        "WALK": "도보 위주 (밀집 도보 이동 고려)",
        "자동차": "자동차 자가용 (주차 편의 고려)",
        "대중교통": "대중교통 (지하철/버스 정류장 접근성 고려)",
        "도보": "도보 위주 (밀집 도보 이동 고려)",
    }


    # 4. 취향 테마 (themes)
    THEME_MAP: Dict[str, str] = {
        "NATURE": "자연·풍경 (자연/전망)",
        "HISTORY_CULTURE": "역사·문화 (문화시설/역사)",
        "FOOD": "미식·맛집",
        "CAFE": "감성 카페·디저트",
        "ACTIVITY": "체험·액티비티 (레포츠)",
        "SHOPPING": "쇼핑",
        "FESTIVAL": "축제·공연",
        "HEALING": "휴식·힐링 (휴양/스파)",
    }

    # 5. 하루 장소 수 (placesPerDay)
    PLACES_PER_DAY_MAP: Dict[str, int] = {
        "RELAXED": 3,  # 2~3곳 여유롭게
        "NORMAL": 4,   # 4~5곳 적당히 (기본)
        "PACKED": 5,   # 6곳 이상 알차게
    }

    # 6. 시작 시간 (startTime)
    START_TIME_MAP: Dict[str, str] = {
        "EARLY": "08:00",
        "NORMAL": "10:00",
        "LATE": "11:00",
    }

    @classmethod
    def resolve_region_name(cls, region_input: str) -> str:
        """지역 코드('6'), 영문('BUSAN'), 한글('부산')을 표준 한글명으로 정규화"""
        clean = region_input.strip()
        if clean in cls.REGION_MAP:
            return cls.REGION_MAP[clean]
        upper = clean.upper()
        if upper in cls.REGION_ALIAS_MAP:
            return cls.REGION_ALIAS_MAP[upper]
        return clean

    @classmethod
    def resolve_region_names(cls, region_inputs: Optional[List[str]]) -> List[str]:
        """복수 지역 코드 배열(['6', '7'])을 표준 한글명 목록(['부산', '울산'])으로 정규화"""
        if not region_inputs:
            return ["부산"]
        resolved = []
        for r in region_inputs:
            name = cls.resolve_region_name(str(r))
            if name and name not in resolved:
                resolved.append(name)
        return resolved or ["부산"]


    @classmethod
    def get_companion_info(cls, companion_code: Optional[str], traveler_count: int = 1) -> Tuple[str, List[str]]:
        """동행 유형 코드 해석 (영문 코드 'FRIENDS' 및 한글 '친구' 둘 다 완벽 지원)"""
        if companion_code:
            clean = companion_code.strip()
            upper_code = clean.upper()
            if upper_code in cls.COMPANION_MAP:
                info = cls.COMPANION_MAP[upper_code]
                return info["name"], info["tags"]
            for k, info in cls.COMPANION_MAP.items():
                if clean in info["name"] or any(t in clean for t in info["tags"]):
                    return info["name"], info["tags"]

        # 코드가 없거나 맞지 않으면 인원수로 추론

        if traveler_count == 1:
            return "혼자", ["혼자"]
        elif traveler_count == 2:
            return "연인/친구", ["커플", "친구"]
        else:
            return "친구/가족", ["친구", "가족"]

    @classmethod
    def get_theme_descriptions(cls, theme_codes: Optional[List[str]]) -> str:
        """취향 코드 배열을 자연어 테마 문자열로 변환"""
        if not theme_codes:
            return "다양한 매력을 골고루 즐기는 종합 여행"
        descs = [cls.THEME_MAP.get(code, code) for code in theme_codes]
        return ", ".join(descs)

    @classmethod
    def get_spots_per_day(cls, code: Optional[str]) -> int:
        if not code:
            return 4
        return cls.PLACES_PER_DAY_MAP.get(code.upper(), 4)

    @classmethod
    def get_start_time_hour(cls, code: Optional[str]) -> int:
        """startTime 코드('EARLY', 'NORMAL', 'LATE') 또는 직접 입력된 시각('09:00', '10:30') 모두 지원"""
        if not code:
            return 10
        clean = str(code).strip().upper()
        if clean == "EARLY":
            return 8
        elif clean == "LATE":
            return 11
        elif clean == "NORMAL":
            return 10
        
        # '09:00' 또는 '10:30' 형태의 직접 시간 문자열 지원
        if ":" in clean:
            try:
                hour = int(clean.split(":")[0])
                return max(6, min(22, hour))
            except ValueError:
                pass
        return 10



code_mapper = CodeMapper()
