import { useEffect, useRef, useState } from "react";
import ChevronDownIcon from "../../components/icons/ChevronDownIcon";
import { createMap, loadMapSdk } from "./mapProvider";
import { getLabelPosition, NATIONAL_VIEW, REGION_GEO } from "./regionGeo";
import styles from "./RegionMap.module.css";

function labelState(code, selectedCode) {
  if (!selectedCode) return "default";
  return code === selectedCode ? "selected" : "dimmed";
}

// regions(코드·이름)와 regionGeo 좌표를 코드로 합친다. 좌표가 없는 지역은 라벨을 그리지 않는다.
function toRegionLabels(regions, selectedCode) {
  return regions.flatMap(({ code, name }) => {
    const geo = REGION_GEO[code];
    if (!geo) {
      console.warn(`[RegionMap] regionGeo 에 좌표가 없는 지역 코드: ${code} (${name})`);
      return [];
    }
    return [{ code, name, ...getLabelPosition(geo), state: labelState(code, selectedCode) }];
  });
}

// regions: [{ code, name }] 지역 목록. 지도를 못 불러와도 왼쪽 질문 흐름은 그대로 동작한다.
export default function RegionMap({ regions, selectedRegionCode, onSelectRegion }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [status, setStatus] = useState("loading"); // 'loading' | 'ready' | 'error'
  const region = regions.find((r) => r.code === selectedRegionCode);
  // 전국 보기(지역 미선택)에서 화면 밖에 있는 지역의 바로가기. 카카오 오버레이가 아닌 React 요소로 겹쳐 그린다.
  const shortcuts =
    status === "ready" && !selectedRegionCode
      ? regions.filter((r) => REGION_GEO[r.code]?.shortcut)
      : [];

  useEffect(() => {
    let cancelled = false;
    loadMapSdk()
      .then(() => {
        if (cancelled) return;
        mapRef.current = createMap(containerRef.current, NATIONAL_VIEW);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
      mapRef.current?.destroy();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (status !== "ready") return;
    const map = mapRef.current;
    map.setRegionLabels(toRegionLabels(regions, selectedRegionCode), { onClick: onSelectRegion });

    const geo = REGION_GEO[selectedRegionCode];
    if (geo) map.focus(geo.center, geo.level);
  }, [status, regions, selectedRegionCode, onSelectRegion]);

  return (
    <section className={styles.map} aria-label="지도">
      <div ref={containerRef} className={styles.canvas} />

      {status === "loading" && <p className={styles.message}>지도를 불러오는 중이에요</p>}
      {status === "error" && (
        <p className={styles.message}>지도를 불러오지 못했어요. 왼쪽 목록에서 지역을 골라주세요.</p>
      )}

      {shortcuts.length > 0 && (
        <div className={styles.shortcuts}>
          {shortcuts.map(({ code, name }) => (
            <button
              key={code}
              type="button"
              className={styles.shortcut}
              aria-label={`${name} 선택`}
              onClick={() => onSelectRegion(code)}
            >
              <span className={styles.shortcutDot} aria-hidden="true" />
              {name}
              <ChevronDownIcon size={14} className={styles.shortcutArrow} />
            </button>
          ))}
        </div>
      )}

      {region && (
        <div className={styles.regionCard}>
          <span className={styles.regionName}>{region.name}</span>
          {/* TODO: 날씨 API 가 생기면 지역 카드에 날씨 요약 추가 */}
        </div>
      )}
    </section>
  );
}
