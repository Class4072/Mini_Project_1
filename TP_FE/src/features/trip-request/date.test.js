import { daysBetween, getTodayKST, isValidDateString } from "./date";

describe("getTodayKST", () => {
  it("UTC 15시 이후는 KST 기준 다음 날이다", () => {
    expect(getTodayKST(new Date("2026-10-20T14:59:59Z"))).toBe("2026-10-20");
    expect(getTodayKST(new Date("2026-10-20T15:00:00Z"))).toBe("2026-10-21");
  });

  it("월·연 경계를 넘긴다", () => {
    expect(getTodayKST(new Date("2026-10-31T16:00:00Z"))).toBe("2026-11-01");
    expect(getTodayKST(new Date("2026-12-31T15:00:00Z"))).toBe("2027-01-01");
  });
});

describe("isValidDateString", () => {
  it("YYYY-MM-DD 형식의 실제 날짜만 허용한다", () => {
    expect(isValidDateString("2026-10-20")).toBe(true);
    expect(isValidDateString("2026-02-30")).toBe(false);
    expect(isValidDateString("2026-1-5")).toBe(false);
    expect(isValidDateString(null)).toBe(false);
  });
});

describe("daysBetween", () => {
  it("월 경계를 넘는 일수를 계산한다", () => {
    expect(daysBetween("2026-10-31", "2026-11-01")).toBe(1);
    expect(daysBetween("2026-02-28", "2026-03-01")).toBe(1);
    expect(daysBetween("2026-11-01", "2026-10-31")).toBe(-1);
  });
});
