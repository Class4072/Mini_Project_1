import SelectableCard from '../../../components/SelectableCard/SelectableCard';
import { REGIONS } from '../../../features/trip-request/tripRequestOptions';
import styles from './RegionGrid.module.css';

// 17개 지역 버튼. 첫 화면과 지역 바꾸기 팝업(compact)에서 함께 쓴다.
export default function RegionGrid({ selectedCode, onSelect, compact = false }) {
  const buttonClassName = [styles.button, compact && styles.compact].filter(Boolean).join(' ');

  return (
    <div className={styles.grid}>
      {REGIONS.map((region) => (
        <SelectableCard
          key={region.value}
          className={buttonClassName}
          selected={region.value === selectedCode}
          onClick={() => onSelect(region.value)}
        >
          {region.label}
        </SelectableCard>
      ))}
    </div>
  );
}
