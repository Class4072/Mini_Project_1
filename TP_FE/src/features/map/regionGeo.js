// 임시 근사값, 확인 필요.
// center 는 줌인할 때의 중심(각 시청·도청 근처), level 은 그 지역이 지도 화면(약 580×780px)에 꽉 차 보이는 카카오 확대 수준.
// label 은 전국 보기에서 라벨을 그릴 위치로, 화면 보고 조정하는 값이다. 없으면 center 에 그린다.
// 키는 tripRequestOptions 의 REGIONS 코드와 같다.

// 전국 보기: 남한 본토가 화면 가운데 오도록. 제주·강원 북쪽 끝은 화면 밖으로 나갈 수 있다.
export const NATIONAL_VIEW = { center: { lat: 36.2, lng: 127.9 }, level: 12 };

export const REGION_GEO = {
  1: { center: { lat: 37.5665, lng: 126.978 }, label: { lat: 37.62, lng: 127.0 }, level: 9 }, // 서울
  2: { center: { lat: 37.4563, lng: 126.7052 }, label: { lat: 37.45, lng: 126.45 }, level: 10 }, // 인천
  31: { center: { lat: 37.2893, lng: 127.0535 }, label: { lat: 37.25, lng: 127.4 }, level: 11 }, // 경기 (수원)
  32: { center: { lat: 37.8853, lng: 127.7298 }, level: 11 }, // 강원 (춘천)
  33: { center: { lat: 36.6358, lng: 127.4913 }, label: { lat: 36.85, lng: 127.85 }, level: 11 }, // 충북 (청주)
  34: { center: { lat: 36.6588, lng: 126.6728 }, label: { lat: 36.55, lng: 126.7 }, level: 11 }, // 충남 (홍성)
  8: { center: { lat: 36.48, lng: 127.289 }, label: { lat: 36.6, lng: 127.1 }, level: 9 }, // 세종
  3: { center: { lat: 36.3504, lng: 127.3845 }, label: { lat: 36.28, lng: 127.5 }, level: 9 }, // 대전
  35: { center: { lat: 36.576, lng: 128.5056 }, level: 11 }, // 경북 (안동·예천)
  4: { center: { lat: 35.8714, lng: 128.6014 }, level: 10 }, // 대구
  7: { center: { lat: 35.5384, lng: 129.3114 }, label: { lat: 35.6, lng: 129.3 }, level: 10 }, // 울산
  6: { center: { lat: 35.1798, lng: 129.075 }, label: { lat: 35.1, lng: 129.1 }, level: 9 }, // 부산
  36: { center: { lat: 35.2383, lng: 128.6922 }, label: { lat: 35.35, lng: 128.2 }, level: 11 }, // 경남 (창원)
  37: { center: { lat: 35.8203, lng: 127.1089 }, level: 11 }, // 전북 (전주)
  38: { center: { lat: 34.8161, lng: 126.4629 }, level: 11 }, // 전남 (무안)
  // 광주 label: 카카오 지도 자체의 "광주" 글자와 겹치지 않게 북서쪽으로
  5: { center: { lat: 35.1601, lng: 126.8514 }, label: { lat: 35.25, lng: 126.8 }, level: 9 }, // 광주
  // 전국 보기에서 화면 밖에 있는 지역은 지도 위 고정 바로가기로 표시 (shortcut: true)
  39: { center: { lat: 33.489, lng: 126.4983 }, level: 10, shortcut: true }, // 제주
};

export function getLabelPosition(geo) {
  return geo.label ?? geo.center;
}
