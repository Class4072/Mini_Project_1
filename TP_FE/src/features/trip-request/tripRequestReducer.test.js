import {
  initialTripRequestState,
  TRIP_REQUEST_ACTIONS as A,
  tripRequestReducer,
} from "./tripRequestReducer";

const TODAY = "2026-10-20";
const reduce = (state, ...actions) => actions.reduce(tripRequestReducer, state);
const next = { type: A.NEXT, today: TODAY };
const prev = { type: A.PREV };

const filled = {
  ...initialTripRequestState,
  regionCode: "6",
  startDate: "2026-10-31",
  endDate: "2026-11-02",
  companionType: "FRIENDS",
  travelerCount: 4,
  transport: "PUBLIC_TRANSIT",
};

describe("초기 상태 (규칙 8)", () => {
  it("optional 기본값: themes [], placesPerDay NORMAL, startTime NORMAL", () => {
    expect(initialTripRequestState).toMatchObject({
      themes: [],
      placesPerDay: "NORMAL",
      startTime: "NORMAL",
      currentStep: "region",
    });
  });
});

describe("지역 선택 (규칙 1)", () => {
  it("region 단계에서 고르면 저장 후 date 로 이동한다", () => {
    const state = reduce(initialTripRequestState, { type: A.SELECT_REGION, regionCode: "39" });
    expect(state.regionCode).toBe("39");
    expect(state.currentStep).toBe("date");
  });

  it("다른 단계에서 바꾸면 regionCode 만 바뀌고 나머지와 단계는 유지된다", () => {
    const before = { ...filled, currentStep: "transport" };
    const after = reduce(before, { type: A.SELECT_REGION, regionCode: "1" });
    expect(after).toEqual({ ...before, regionCode: "1" });
  });
});

describe("다음 버튼 (규칙 2)", () => {
  it("조건을 만족하지 않으면 이동하지 않는다", () => {
    const state = { ...initialTripRequestState, regionCode: "1", currentStep: "date" };
    expect(reduce(state, next).currentStep).toBe("date");

    const past = { ...state, startDate: "2026-10-19", endDate: "2026-10-21" };
    expect(reduce(past, next).currentStep).toBe("date");
  });

  it("필수 단계를 순서대로 진행한다", () => {
    let state = reduce(initialTripRequestState, { type: A.SELECT_REGION, regionCode: "1" });
    state = reduce(state, { type: A.SET_DATES, startDate: TODAY, endDate: "2026-10-21" }, next);
    expect(state.currentStep).toBe("companion");
    state = reduce(state, { type: A.SELECT_COMPANION, companionType: "COUPLE" }, next);
    expect(state.currentStep).toBe("travelerCount");
    state = reduce(state, { type: A.SET_TRAVELER_COUNT, travelerCount: 1 }, next);
    expect(state.currentStep).toBe("travelerCount");
    state = reduce(state, { type: A.SET_TRAVELER_COUNT, travelerCount: 3 }, next);
    expect(state.currentStep).toBe("transport");
    state = reduce(state, { type: A.SELECT_TRANSPORT, transport: "CAR" }, next);
    expect(state.currentStep).toBe("optional");
  });

  it("optional 단계에서는 더 이동하지 않는다", () => {
    const state = { ...filled, currentStep: "optional" };
    expect(reduce(state, next)).toBe(state);
  });
});

describe("동행과 인원 (규칙 3)", () => {
  const atCompanion = {
    ...filled,
    companionType: null,
    travelerCount: null,
    currentStep: "companion",
  };
  const select = (companionType) => ({ type: A.SELECT_COMPANION, companionType });

  it("SOLO 를 고르면 travelerCount = 1 이고 앞으로 갈 때 인원 단계를 건너뛴다", () => {
    const state = reduce(atCompanion, select("SOLO"));
    expect(state.travelerCount).toBe(1);
    expect(reduce(state, next).currentStep).toBe("transport");
  });

  it("SOLO 일 때 transport 에서 이전을 누르면 companion 으로 간다", () => {
    const state = reduce(atCompanion, select("SOLO"), next);
    expect(reduce(state, prev).currentStep).toBe("companion");
  });

  it("SOLO 에서 다른 동행으로 바꾸면 travelerCount = 2", () => {
    const state = reduce(atCompanion, select("SOLO"), select("FRIENDS"));
    expect(state.travelerCount).toBe(2);
    expect(reduce(state, next).currentStep).toBe("travelerCount");
  });

  it("처음 SOLO 가 아닌 동행을 고르면 travelerCount = 2", () => {
    const state = reduce(atCompanion, select("FRIENDS"));
    expect(state.travelerCount).toBe(2);
    expect(reduce(state, next).currentStep).toBe("travelerCount");
  });

  it("SOLO 가 아닌 동행끼리 바꾸면 인원을 유지한다", () => {
    const state = reduce(
      atCompanion,
      select("FRIENDS"),
      { type: A.SET_TRAVELER_COUNT, travelerCount: 3 },
      select("COUPLE"),
    );
    expect(state.travelerCount).toBe(3);
  });
});

describe("이전 버튼 (규칙 4)", () => {
  it("바로 앞 필수 단계로 간다", () => {
    expect(reduce({ ...filled, currentStep: "transport" }, prev).currentStep).toBe("travelerCount");
    expect(reduce({ ...filled, currentStep: "travelerCount" }, prev).currentStep).toBe("companion");
    expect(reduce({ ...filled, currentStep: "companion" }, prev).currentStep).toBe("date");
    expect(reduce({ ...filled, currentStep: "optional" }, prev).currentStep).toBe("transport");
  });

  it("date 에서는 이전이 없다", () => {
    const state = { ...filled, currentStep: "date" };
    expect(reduce(state, prev)).toBe(state);
  });
});

describe("답한 내용 칩 (규칙 5)", () => {
  it("해당 단계로 이동하고 답은 유지된다", () => {
    const before = { ...filled, currentStep: "optional" };
    const after = reduce(before, { type: A.GO_TO_STEP, step: "companion" });
    expect(after).toEqual({ ...before, currentStep: "companion" });
  });

  it("이동 후 다음 버튼은 평소 순서대로 진행한다", () => {
    const state = reduce(
      { ...filled, currentStep: "optional" },
      { type: A.GO_TO_STEP, step: "date" },
      next,
    );
    expect(state.currentStep).toBe("companion");
    expect(reduce(state, next, next, next).currentStep).toBe("optional");
  });

  it("보이지 않는 단계나 필수가 아닌 단계로는 이동하지 않는다", () => {
    const solo = { ...filled, companionType: "SOLO", travelerCount: 1, currentStep: "optional" };
    expect(reduce(solo, { type: A.GO_TO_STEP, step: "travelerCount" })).toBe(solo);
    expect(reduce(solo, { type: A.GO_TO_STEP, step: "region" })).toBe(solo);
  });
});

describe("취향 (규칙 6)", () => {
  const toggle = (theme) => ({ type: A.TOGGLE_THEME, theme });
  const base = { ...filled, currentStep: "optional" };

  it("고르면 추가, 다시 누르면 해제", () => {
    expect(reduce(base, toggle("FOOD")).themes).toEqual(["FOOD"]);
    expect(reduce(base, toggle("FOOD"), toggle("CAFE"), toggle("FOOD")).themes).toEqual(["CAFE"]);
  });

  it("3개 선택된 상태에서 4번째는 무시한다", () => {
    const three = reduce(base, toggle("FOOD"), toggle("CAFE"), toggle("NATURE"));
    expect(reduce(three, toggle("SHOPPING"))).toBe(three);
    expect(reduce(three, toggle("CAFE")).themes).toEqual(["FOOD", "NATURE"]);
  });

  it("골고루를 누르면 빈 배열이 된다", () => {
    const state = reduce(base, toggle("FOOD"), toggle("CAFE"), { type: A.CLEAR_THEMES });
    expect(state.themes).toEqual([]);
  });
});

describe("optional 설정", () => {
  it("하루 몇 곳과 시작 시간을 바꾼다", () => {
    const state = reduce(
      { ...filled, currentStep: "optional" },
      { type: A.SET_PLACES_PER_DAY, placesPerDay: "PACKED" },
      { type: A.SET_START_TIME, startTime: "EARLY" },
    );
    expect(state.placesPerDay).toBe("PACKED");
    expect(state.startTime).toBe("EARLY");
  });
});
