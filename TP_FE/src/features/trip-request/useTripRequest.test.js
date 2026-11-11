import { act, renderHook } from "@testing-library/react";
import { useTripRequest } from "./useTripRequest";

const getToday = () => "2026-10-20";

describe("useTripRequest", () => {
  it("질문 흐름을 끝까지 진행하고 요청 body 를 만든다", () => {
    const { result } = renderHook(() => useTripRequest({ getToday }));
    const run = (fn) => act(() => fn(result.current.actions));

    expect(result.current.progress).toBeNull();
    run((a) => a.selectRegion("6"));
    expect(result.current.state.currentStep).toBe("date");
    expect(result.current.progress).toEqual({ current: 1, total: 4 });

    run((a) => a.setDates("2026-10-19", "2026-10-21"));
    expect(result.current.canGoNext).toBe(false);
    run((a) => a.setDates("2026-10-31", "2026-11-01"));
    expect(result.current.canGoNext).toBe(true);

    run((a) => a.next());
    run((a) => a.selectCompanion("SOLO"));
    expect(result.current.progress).toEqual({ current: 2, total: 3 });
    run((a) => a.next());
    expect(result.current.state.currentStep).toBe("transport");

    run((a) => a.selectTransport("WALK"));
    run((a) => a.next());
    expect(result.current.state.currentStep).toBe("optional");
    expect(result.current.canSubmit).toBe(true);

    run((a) => a.toggleTheme("HEALING"));
    expect(result.current.requestBody).toEqual({
      regionCodes: ["6"],
      startDate: "2026-10-31",
      endDate: "2026-11-01",
      companionType: "SOLO",
      travelerCount: 1,
      transport: "WALK",
      themes: ["HEALING"],
      placesPerDay: "NORMAL",
      startTime: "NORMAL",
    });
  });
});
