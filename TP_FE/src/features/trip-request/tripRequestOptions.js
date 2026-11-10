// 내일 팀 회의 후 변경 예정: 아래 value(코드값)는 모두 임시다. label 은 화면 문구.

export const STEPS = ['region', 'date', 'companion', 'travelerCount', 'transport', 'optional'];
export const REQUIRED_STEPS = ['date', 'companion', 'travelerCount', 'transport'];

// 지역 코드는 TourAPI areaCode 가정. 배열 순서 = 화면 표시 순서.
export const REGIONS = [
  { value: '1', label: '서울' },
  { value: '2', label: '인천' },
  { value: '31', label: '경기' },
  { value: '32', label: '강원' },
  { value: '33', label: '충북' },
  { value: '34', label: '충남' },
  { value: '8', label: '세종' },
  { value: '3', label: '대전' },
  { value: '35', label: '경북' },
  { value: '4', label: '대구' },
  { value: '7', label: '울산' },
  { value: '6', label: '부산' },
  { value: '36', label: '경남' },
  { value: '37', label: '전북' },
  { value: '38', label: '전남' },
  { value: '5', label: '광주' },
  { value: '39', label: '제주' },
];

export const SOLO = 'SOLO';

export const COMPANIONS = [
  { value: SOLO, label: '혼자' },
  { value: 'COUPLE', label: '연인·부부' },
  { value: 'FRIENDS', label: '친구' },
  { value: 'FAMILY_WITH_KIDS', label: '아이와 함께' },
  { value: 'FAMILY_WITH_PARENTS', label: '부모님과 함께' },
  { value: 'GROUP', label: '단체' },
];

export const TRAVELER_COUNT_PRESETS = [
  { value: 2, label: '2명' },
  { value: 3, label: '3명' },
  { value: 4, label: '4명' },
  { value: 5, label: '5명' },
  { value: 6, label: '6명 이상' },
];

export const TRANSPORTS = [
  {
    value: 'CAR',
    label: '자동차',
    description: '주차할 수 있는 곳 위주로, 조금 멀어도 한 번에 이어서 돌아요.',
  },
  {
    value: 'PUBLIC_TRANSIT',
    label: '대중교통',
    description: '역·정류장에서 가까운 곳 위주로 짜요.',
  },
  { value: 'WALK', label: '도보 위주', description: '걸어서 이동할 수 있는 거리 안에서 묶어요.' },
];

// "골고루"는 별도 코드 없이 themes = [] 로 표현한다.
export const THEMES = [
  { value: 'NATURE', label: '자연·풍경' },
  { value: 'HISTORY_CULTURE', label: '역사·문화' },
  { value: 'FOOD', label: '맛집' },
  { value: 'CAFE', label: '카페' },
  { value: 'ACTIVITY', label: '체험·액티비티' },
  { value: 'SHOPPING', label: '쇼핑' },
  { value: 'FESTIVAL', label: '축제·공연' },
  { value: 'HEALING', label: '휴식·힐링' },
];

export const PLACES_PER_DAY = [
  { value: 'RELAXED', label: '여유롭게', description: '2~3곳' },
  { value: 'NORMAL', label: '적당히', description: '4~5곳' },
  { value: 'PACKED', label: '알차게', description: '6곳 이상' },
];

export const START_TIMES = [
  { value: 'EARLY', label: '아침 일찍', time: '08:00' },
  { value: 'NORMAL', label: '보통', time: '10:00' },
  { value: 'LATE', label: '느긋하게', time: '11:00', note: '퇴실 후' },
];

export const END_TIME = '21:00';

export const DEFAULT_PLACES_PER_DAY = 'NORMAL';
export const DEFAULT_START_TIME = 'NORMAL';

// 제약: null 이면 검사하지 않는다. (개발 단계는 제한 없음, 숫자만 넣으면 동작)
export const MAX_TRIP_DAYS = null; // 여행 기간(출발일·도착일 포함 일수) 상한
export const MAX_DAYS_AHEAD = null; // 오늘로부터 출발일까지 최대 일수
export const MAX_TRAVELERS = null;
export const MAX_THEMES = 3;
