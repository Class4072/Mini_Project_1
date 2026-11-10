const sdkScripts = () => document.querySelectorAll('script[src^="https://dapi.kakao.com/"]');

// 모듈 안의 로딩 상태를 테스트마다 새로 시작한다.
async function freshLoadMapSdk() {
  let loadMapSdk;
  await jest.isolateModulesAsync(async () => {
    ({ loadMapSdk } = await import('./loadMapSdk'));
  });
  return loadMapSdk;
}

describe('loadMapSdk', () => {
  beforeEach(() => {
    sdkScripts().forEach((script) => script.remove());
    window.kakao = { maps: { load: jest.fn((callback) => callback()) } };
  });

  afterEach(() => {
    delete window.kakao;
  });

  it('여러 번 호출해도 script 태그는 하나만 넣고, autoload=false 로 불러온다', async () => {
    const loadMapSdk = await freshLoadMapSdk();
    const first = loadMapSdk();
    const second = loadMapSdk();
    loadMapSdk();

    expect(second).toBe(first);
    expect(sdkScripts()).toHaveLength(1);
    const src = sdkScripts()[0].getAttribute('src');
    expect(src).toContain('appkey=test-kakao-key');
    expect(src).toContain('autoload=false');

    sdkScripts()[0].dispatchEvent(new Event('load'));
    await expect(first).resolves.toBeUndefined();
    expect(window.kakao.maps.load).toHaveBeenCalledTimes(1);

    // 준비된 뒤에도 다시 넣지 않는다
    loadMapSdk();
    expect(sdkScripts()).toHaveLength(1);
  });

  it('불러오기에 실패하면 거부하고, 다음 호출에서 다시 시도한다', async () => {
    const loadMapSdk = await freshLoadMapSdk();
    const first = loadMapSdk();
    sdkScripts()[0].dispatchEvent(new Event('error'));
    await expect(first).rejects.toThrow();
    expect(sdkScripts()).toHaveLength(0);

    loadMapSdk();
    expect(sdkScripts()).toHaveLength(1);
  });

  it('키가 없으면 script 를 넣지 않고 거부한다', async () => {
    let loadMapSdk;
    await jest.isolateModulesAsync(async () => {
      jest.doMock('../../../config/env', () => ({ env: { kakaoMapKey: '' } }));
      ({ loadMapSdk } = await import('./loadMapSdk'));
    });
    await expect(loadMapSdk()).rejects.toThrow('VITE_KAKAO_MAP_KEY');
    expect(sdkScripts()).toHaveLength(0);
  });
});
