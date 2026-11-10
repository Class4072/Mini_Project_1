import { env } from '../../../config/env';

const SDK_URL = 'https://dapi.kakao.com/v2/maps/sdk.js';

let sdkPromise = null;

// 카카오맵 SDK 를 한 번만 불러온다. 실패하면 다음 호출에서 다시 시도할 수 있게 초기화한다.
export function loadMapSdk() {
  if (sdkPromise) return sdkPromise;

  let script = null;
  sdkPromise = new Promise((resolve, reject) => {
    if (!env.kakaoMapKey) {
      reject(new Error('VITE_KAKAO_MAP_KEY 가 설정되지 않았습니다.'));
      return;
    }
    script = document.createElement('script');
    script.src = `${SDK_URL}?appkey=${encodeURIComponent(env.kakaoMapKey)}&autoload=false`;
    script.async = true;
    script.onload = () => {
      if (!window.kakao?.maps) {
        reject(new Error('카카오맵 SDK 를 초기화하지 못했습니다.'));
        return;
      }
      window.kakao.maps.load(() => resolve());
    };
    script.onerror = () => reject(new Error('카카오맵 SDK 를 불러오지 못했습니다.'));
    document.head.appendChild(script);
  }).catch((error) => {
    script?.remove();
    sdkPromise = null;
    throw error;
  });

  return sdkPromise;
}
