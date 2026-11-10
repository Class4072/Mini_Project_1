// Jest 용 env mock. jest.setup.js 에서 jest.mock('./src/config/env') 로 자동 적용된다.
export const env = {
  apiBaseUrl: '',
  kakaoMapKey: 'test-kakao-key',
  useMock: true,
  isDev: false,
};
