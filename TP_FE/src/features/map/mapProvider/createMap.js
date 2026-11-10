import { renderRegionLabels } from './regionLabels';

const ZOOM_ANIMATION_MS = 300;
const noop = () => {};

function isSameCenter(a, b) {
  return Math.abs(a.getLat() - b.getLat()) < 1e-6 && Math.abs(a.getLng() - b.getLng()) < 1e-6;
}

// 카카오 지도를 만들고, 카카오 객체 대신 focus / setRegionLabels / destroy 핸들을 돌려준다.
// loadMapSdk() 가 끝난 뒤에 호출해야 한다.
export function createMap(container, { center, level }) {
  const { maps } = window.kakao;
  const map = new maps.Map(container, {
    center: new maps.LatLng(center.lat, center.lng),
    level,
  });
  map.addControl(new maps.ZoomControl(), maps.ControlPosition.BOTTOMRIGHT);

  let clearLabels = noop;
  let cancelPendingZoom = noop;

  return {
    // 중심을 부드럽게 옮긴 뒤(idle) 확대 수준을 바꾼다. 연속 호출되면 이전 예약은 취소한다.
    focus({ lat, lng }, nextLevel) {
      cancelPendingZoom();
      const target = new maps.LatLng(lat, lng);
      const zoom = () => {
        if (map.getLevel() !== nextLevel) {
          map.setLevel(nextLevel, { animate: { duration: ZOOM_ANIMATION_MS } });
        }
      };

      if (isSameCenter(map.getCenter(), target)) {
        zoom();
        return;
      }
      const handleIdle = () => {
        cancelPendingZoom();
        zoom();
      };
      maps.event.addListener(map, 'idle', handleIdle);
      cancelPendingZoom = () => {
        maps.event.removeListener(map, 'idle', handleIdle);
        cancelPendingZoom = noop;
      };
      map.panTo(target);
    },

    setRegionLabels(labels, options) {
      clearLabels();
      clearLabels = renderRegionLabels(maps, map, labels, options);
    },

    destroy() {
      cancelPendingZoom();
      clearLabels();
      clearLabels = noop;
    },
  };
}
