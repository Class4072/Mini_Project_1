import { act, renderHook } from "@testing-library/react";
import { generateItinerary } from "./tripRequestApi";
import { GENERATE_ERROR_MESSAGES, useGenerateItinerary } from "./useGenerateItinerary";

jest.mock("./tripRequestApi");

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useGenerateItinerary", () => {
  beforeEach(() => jest.clearAllMocks());

  it("제출 중에는 다시 호출해도 무시하고, 성공하면 itineraryId 와 함께 onSuccess 를 부른다", async () => {
    const request = deferred();
    generateItinerary.mockReturnValue(request.promise);
    const onSuccess = jest.fn();
    const { result } = renderHook(() => useGenerateItinerary({ onSuccess }));

    let first;
    let second;
    act(() => {
      first = result.current.submit({ a: 1 });
      second = result.current.submit({ a: 1 });
    });
    expect(generateItinerary).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe("submitting");
    await expect(second).resolves.toBeNull();

    await act(async () => request.resolve({ itineraryId: "mock-1" }));
    await expect(first).resolves.toBe("mock-1");
    expect(onSuccess).toHaveBeenCalledWith("mock-1");
    expect(result.current.status).toBe("idle");
  });

  it.each([
    ["ECONNABORTED", GENERATE_ERROR_MESSAGES.timeout],
    ["ETIMEDOUT", GENERATE_ERROR_MESSAGES.timeout],
    ["ERR_BAD_RESPONSE", GENERATE_ERROR_MESSAGES.default],
  ])("실패 코드 %s 이면 알맞은 문구로 error 상태가 된다", async (code, message) => {
    generateItinerary.mockRejectedValue(Object.assign(new Error("fail"), { code }));
    const onSuccess = jest.fn();
    const { result } = renderHook(() => useGenerateItinerary({ onSuccess }));

    await act(async () => {
      await expect(result.current.submit({})).resolves.toBeNull();
    });
    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toBe(message);
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("실패한 뒤 다시 제출할 수 있고, 제출하면 오류 문구가 지워진다", async () => {
    generateItinerary.mockRejectedValueOnce(new Error("fail"));
    const { result } = renderHook(() => useGenerateItinerary());
    await act(() => result.current.submit({}));
    expect(result.current.errorMessage).toBe(GENERATE_ERROR_MESSAGES.default);

    generateItinerary.mockResolvedValueOnce({ itineraryId: "id-2" });
    let id;
    await act(async () => {
      id = await result.current.submit({});
    });
    expect(id).toBe("id-2");
    expect(result.current.errorMessage).toBeNull();
    expect(generateItinerary).toHaveBeenCalledTimes(2);
  });
});
