// 백엔드가 준비되기 전까지 쓰는 가짜 일정 생성. env.useMock 이 true 일 때 tripRequestApi 가 사용한다.
export const MOCK_DELAY_MS = 3000;

export function generateItineraryMock() {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ itineraryId: `mock-${Date.now()}` }), MOCK_DELAY_MS);
  });
}
