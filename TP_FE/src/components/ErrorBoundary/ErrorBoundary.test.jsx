import { fireEvent, render, screen } from "@testing-library/react";
import ErrorBoundary from "./ErrorBoundary";

// shouldThrow.current 가 true 면 렌더링 중 오류를 던진다.
const shouldThrow = { current: true };

function Child() {
  if (shouldThrow.current) throw new Error("render failed");
  return <p>정상 화면</p>;
}

describe("ErrorBoundary", () => {
  let consoleError;

  beforeEach(() => {
    shouldThrow.current = true;
    // React 가 잡은 렌더링 오류를 console.error 로 찍으므로 테스트 출력에서 숨긴다.
    consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleError.mockRestore();
  });

  it("오류가 없으면 자식을 그대로 보여준다", () => {
    shouldThrow.current = false;
    render(
      <ErrorBoundary>
        <Child />
      </ErrorBoundary>,
    );
    expect(screen.getByText("정상 화면")).toBeInTheDocument();
  });

  it("자식이 렌더링 중 오류를 던지면 기본 fallback 을 보여주고 logger.error 로 기록한다", () => {
    render(
      <ErrorBoundary>
        <Child />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("화면을 불러오지 못했어요");
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
    expect(consoleError).toHaveBeenCalledWith(
      "[ERROR] [ErrorBoundary] 렌더링 오류",
      expect.objectContaining({ message: "render failed" }),
      expect.any(String),
    );
  });

  it("fallback 을 주면 그 내용을 보여준다", () => {
    render(
      <ErrorBoundary fallback={<p>대신 보여줄 내용</p>}>
        <Child />
      </ErrorBoundary>,
    );
    expect(screen.getByText("대신 보여줄 내용")).toBeInTheDocument();
  });

  it("fallback 이 함수면 reset 을 넘겨 호출한다", () => {
    render(
      <ErrorBoundary fallback={(reset) => <button onClick={reset}>복구</button>}>
        <Child />
      </ErrorBoundary>,
    );
    shouldThrow.current = false;
    fireEvent.click(screen.getByRole("button", { name: "복구" }));
    expect(screen.getByText("정상 화면")).toBeInTheDocument();
  });

  it("다시 시도를 누르면 오류 상태가 초기화되어 정상 자식이 다시 보인다", () => {
    render(
      <ErrorBoundary>
        <Child />
      </ErrorBoundary>,
    );
    shouldThrow.current = false;
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(screen.getByText("정상 화면")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("resetKeys 가 바뀌면 오류 상태가 초기화된다", () => {
    const { rerender } = render(
      <ErrorBoundary resetKeys={["/a"]}>
        <Child />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();

    shouldThrow.current = false;
    rerender(
      <ErrorBoundary resetKeys={["/a"]}>
        <Child />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();

    rerender(
      <ErrorBoundary resetKeys={["/b"]}>
        <Child />
      </ErrorBoundary>,
    );
    expect(screen.getByText("정상 화면")).toBeInTheDocument();
  });
});
