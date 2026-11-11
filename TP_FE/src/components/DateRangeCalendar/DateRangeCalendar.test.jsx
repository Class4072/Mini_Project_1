import { fireEvent, render, screen } from "@testing-library/react";
import DateRangeCalendar from "./DateRangeCalendar";

const MIN = "2026-10-20";

function setup(props) {
  const onChange = jest.fn();
  render(<DateRangeCalendar minDate={MIN} onChange={onChange} {...props} />);
  return onChange;
}

const click = (label) => fireEvent.click(screen.getByRole("button", { name: label }));

describe("DateRangeCalendar", () => {
  it("출발일이 있으면 그 달을 연다", () => {
    setup({ startDate: "2026-12-24", endDate: null });
    expect(screen.getByText("2026년 12월")).toBeInTheDocument();
  });

  it("출발일이 없으면 클릭한 날이 출발일이 된다", () => {
    const onChange = setup({ startDate: null, endDate: null });
    click("2026년 10월 25일 일요일");
    expect(onChange).toHaveBeenCalledWith("2026-10-25", null);
  });

  it("출발일만 있고 그 이후(같은 날 포함)를 누르면 도착일이 된다", () => {
    const onChange = setup({ startDate: "2026-10-25", endDate: null });
    click("2026년 10월 27일 화요일");
    click("2026년 10월 25일 일요일");
    expect(onChange).toHaveBeenNthCalledWith(1, "2026-10-25", "2026-10-27");
    expect(onChange).toHaveBeenNthCalledWith(2, "2026-10-25", "2026-10-25");
  });

  it("출발일만 있고 그보다 앞을 누르면 새 출발일이 된다", () => {
    const onChange = setup({ startDate: "2026-10-25", endDate: null });
    click("2026년 10월 22일 목요일");
    expect(onChange).toHaveBeenCalledWith("2026-10-22", null);
  });

  it("출발일·도착일이 모두 있으면 새 출발일부터 다시 고른다", () => {
    const onChange = setup({ startDate: "2026-10-25", endDate: "2026-10-27" });
    click("2026년 10월 30일 금요일");
    expect(onChange).toHaveBeenCalledWith("2026-10-30", null);
  });

  it("월을 넘겨 연말·연초를 표시한다", () => {
    setup({ startDate: "2026-12-01", endDate: null });
    click("다음 달");
    expect(screen.getByText("2027년 1월")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2027년 1월 1일 금요일" })).toBeEnabled();
    click("이전 달");
    click("이전 달");
    expect(screen.getByText("2026년 11월")).toBeInTheDocument();
  });
});
