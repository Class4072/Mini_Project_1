import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import MainPage from "./MainPage";

// 지도 컴포넌트가 렌더링 중 오류를 던지는 상황을 만든다.
jest.mock("../../features/map/RegionMap", () => ({
  __esModule: true,
  default: function BrokenRegionMap() {
    throw new Error("map render failed");
  },
}));
jest.mock("../../features/trip-request/tripRequestApi");

describe("MainPage 지도 렌더링 오류", () => {
  let consoleError;

  beforeEach(() => {
    consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleError.mockRestore();
  });

  it("지도 자리에만 오류 문구와 다시 시도를 보여주고, 질문 패널은 계속 쓸 수 있다", () => {
    render(
      <MemoryRouter>
        <MainPage />
      </MemoryRouter>,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("지도를 표시하지 못했어요");
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "부산" }));
    expect(screen.getByRole("heading", { name: "언제 가나요?" })).toBeInTheDocument();
  });
});
