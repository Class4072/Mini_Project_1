import BusIcon from "../../../components/icons/BusIcon";
import CarIcon from "../../../components/icons/CarIcon";
import WalkIcon from "../../../components/icons/WalkIcon";
import SelectableCard from "../../../components/SelectableCard/SelectableCard";
import { TRANSPORTS } from "../../../features/trip-request/tripRequestOptions";
import styles from "./TransportStep.module.css";

// 코드값이 바뀌면 여기 키도 함께 바꾼다.
const TRANSPORT_ICONS = {
  CAR: CarIcon,
  PUBLIC_TRANSIT: BusIcon,
  WALK: WalkIcon,
};

export default function TransportStep({ value, onSelect }) {
  return (
    <div className={styles.list}>
      {TRANSPORTS.map((transport) => {
        const Icon = TRANSPORT_ICONS[transport.value];
        return (
          <SelectableCard
            key={transport.value}
            className={styles.card}
            selected={transport.value === value}
            onClick={() => onSelect(transport.value)}
          >
            <span className={styles.iconBox}>{Icon && <Icon size={24} />}</span>
            <span className={styles.text}>
              <span className={styles.name}>{transport.label}</span>
              <span className={styles.description}>{transport.description}</span>
            </span>
          </SelectableCard>
        );
      })}
    </div>
  );
}
