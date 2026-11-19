import { toAreaCodes } from "./tripRequestOptions";

export function toTripRequest(state) {
  return {
    // 여러 지역 선택을 고려해 배열로 보낸다. 통합 지역(전남광주)은 TourAPI 코드 여러 개로 펼친다.
    regionCodes: toAreaCodes(state.regionCode),
    startDate: state.startDate,
    endDate: state.endDate,
    companionType: state.companionType,
    travelerCount: state.travelerCount,
    transport: state.transport,
    themes: [...state.themes],
    placesPerDay: state.placesPerDay,
    startTime: state.startTime,
  };
}
