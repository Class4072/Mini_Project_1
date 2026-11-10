import { apiClient } from "../../api/client";
import { env } from "../../config/env";
import {
  GENERATE_ITINERARY_PATH,
  GENERATE_ITINERARY_TIMEOUT_MS,
  generateItinerary,
} from "./tripRequestApi";
import { generateItineraryMock, MOCK_DELAY_MS } from "./tripRequestApi.mock";

jest.mock("../../api/client", () => ({ apiClient: { post: jest.fn() } }));

const REQUEST_BODY = { regionCodes: ["6"], startDate: "2026-11-01", endDate: "2026-11-03" };

describe("generateItineraryMock", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it(`MOCK_DELAY_MS 뒤에 'mock-' 으로 시작하는 id 를 돌려준다`, async () => {
    const onResolved = jest.fn();
    const promise = generateItineraryMock(REQUEST_BODY).then(onResolved);

    await jest.advanceTimersByTimeAsync(MOCK_DELAY_MS - 1);
    expect(onResolved).not.toHaveBeenCalled();

    await jest.advanceTimersByTimeAsync(1);
    await promise;
    expect(onResolved).toHaveBeenCalledWith({ itineraryId: expect.stringMatching(/^mock-\d+$/) });
  });
});

describe("generateItinerary", () => {
  const original = { ...env };

  beforeEach(() => jest.clearAllMocks());
  afterEach(() => Object.assign(env, original));

  it("useMock 이 false 면 정해진 주소로 요청 본문을 POST 하고, 타임아웃은 120초다", async () => {
    env.useMock = false;
    apiClient.post.mockResolvedValue({ data: { itineraryId: "abc-123" } });

    await expect(generateItinerary(REQUEST_BODY)).resolves.toEqual({ itineraryId: "abc-123" });
    expect(GENERATE_ITINERARY_PATH).toBe("/api/v1/itinerary/itineraries/generate");
    expect(apiClient.post).toHaveBeenCalledWith(GENERATE_ITINERARY_PATH, REQUEST_BODY, {
      timeout: GENERATE_ITINERARY_TIMEOUT_MS,
    });
    expect(GENERATE_ITINERARY_TIMEOUT_MS).toBe(120000);
  });

  it("요청이 실패하면 그 오류를 그대로 던진다", async () => {
    env.useMock = false;
    const error = Object.assign(new Error("timeout"), { code: "ECONNABORTED" });
    apiClient.post.mockRejectedValue(error);
    await expect(generateItinerary(REQUEST_BODY)).rejects.toBe(error);
  });

  it("useMock 이 true 면 실제 요청 없이 가짜 응답을 돌려준다", async () => {
    jest.useFakeTimers();
    env.useMock = true;
    const promise = generateItinerary(REQUEST_BODY);
    await jest.advanceTimersByTimeAsync(MOCK_DELAY_MS);

    await expect(promise).resolves.toEqual({ itineraryId: expect.stringMatching(/^mock-/) });
    expect(apiClient.post).not.toHaveBeenCalled();
    jest.useRealTimers();
  });

  it("개발 모드에서만 걸린 시간을 console.info 로 남긴다", async () => {
    const info = jest.spyOn(console, "info").mockImplementation(() => {});
    env.useMock = false;
    apiClient.post.mockResolvedValue({ data: { itineraryId: "abc-123" } });

    env.isDev = false;
    await generateItinerary(REQUEST_BODY);
    expect(info).not.toHaveBeenCalled();

    env.isDev = true;
    await generateItinerary(REQUEST_BODY);
    expect(info).toHaveBeenCalledWith(expect.stringMatching(/^\[일정 생성\] \d+ms$/));
    info.mockRestore();
  });
});
