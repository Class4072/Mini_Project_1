import { toTripRequest } from "./toTripRequest";
import { initialTripRequestState } from "./tripRequestReducer";

describe("toTripRequest", () => {
  it("상태를 API 요청 body 로 변환한다", () => {
    const state = {
      ...initialTripRequestState,
      regionCode: "39",
      startDate: "2026-10-31",
      endDate: "2026-11-02",
      companionType: "COUPLE",
      travelerCount: 2,
      transport: "CAR",
      themes: ["FOOD", "CAFE"],
      placesPerDay: "RELAXED",
      startTime: "LATE",
      currentStep: "optional",
    };

    expect(toTripRequest(state)).toEqual({
      regionCodes: ["39"],
      startDate: "2026-10-31",
      endDate: "2026-11-02",
      companionType: "COUPLE",
      travelerCount: 2,
      transport: "CAR",
      themes: ["FOOD", "CAFE"],
      placesPerDay: "RELAXED",
      startTime: "LATE",
    });
  });

  it("골고루(빈 themes)와 기본값을 그대로 보내고 currentStep 은 포함하지 않는다", () => {
    const body = toTripRequest({ ...initialTripRequestState, regionCode: "1" });
    expect(body).toMatchObject({ themes: [], placesPerDay: "NORMAL", startTime: "NORMAL" });
    expect(body).not.toHaveProperty("currentStep");
  });
});
