// Jest 용 mapProvider mock. 테스트에서 jest.mock('.../features/map/mapProvider') 로 적용한다.
// createMap 이 돌려준 핸들은 createMap.mock.results[n].value 로 꺼내 검사한다.
export const loadMapSdk = jest.fn(() => Promise.resolve());

export const createMap = jest.fn(() => ({
  focus: jest.fn(),
  setRegionLabels: jest.fn(),
  destroy: jest.fn(),
}));
