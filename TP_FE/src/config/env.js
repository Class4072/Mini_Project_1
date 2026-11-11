// import.meta.env 접근은 이 파일에서만 한다. (Jest 에서는 이 모듈을 mock 한다)
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "",
  kakaoMapKey: import.meta.env.VITE_KAKAO_MAP_API_KEY ?? "",
  useMock: import.meta.env.VITE_USE_MOCK === "true",
  isDev: import.meta.env.DEV,
};
