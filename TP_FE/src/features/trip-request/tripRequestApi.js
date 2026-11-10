import { apiClient } from '../../api/client';
import { env } from '../../config/env';
import { generateItineraryMock } from './tripRequestApi.mock';

// 임시 주소, 백엔드 확정 후 변경
export const GENERATE_ITINERARY_PATH = '/api/v1/itinerary/itineraries/generate';

// LLM 생성이 오래 걸려 이 요청만 타임아웃을 늘린다.
export const GENERATE_ITINERARY_TIMEOUT_MS = 120_000;

async function postGenerateItinerary(requestBody) {
  const { data } = await apiClient.post(GENERATE_ITINERARY_PATH, requestBody, {
    timeout: GENERATE_ITINERARY_TIMEOUT_MS,
  });
  return { itineraryId: data.itineraryId };
}

// requestBody 는 toTripRequest(state) 결과. → Promise<{ itineraryId }>
export async function generateItinerary(requestBody) {
  const startedAt = performance.now();
  try {
    const request = env.useMock ? generateItineraryMock : postGenerateItinerary;
    return await request(requestBody);
  } finally {
    // 실제 생성 시간 측정용 (개발 모드에서만)
    if (env.isDev) console.info(`[일정 생성] ${Math.round(performance.now() - startedAt)}ms`);
  }
}
