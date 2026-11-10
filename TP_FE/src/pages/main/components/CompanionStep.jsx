import ChildIcon from "../../../components/icons/ChildIcon";
import ElderIcon from "../../../components/icons/ElderIcon";
import FriendsIcon from "../../../components/icons/FriendsIcon";
import GroupIcon from "../../../components/icons/GroupIcon";
import HeartIcon from "../../../components/icons/HeartIcon";
import PersonIcon from "../../../components/icons/PersonIcon";
import SelectableCard from "../../../components/SelectableCard/SelectableCard";
import { COMPANIONS } from "../../../features/trip-request/tripRequestOptions";
import styles from "./CompanionStep.module.css";

// 코드값이 바뀌면 여기 키도 함께 바꾼다.
const COMPANION_ICONS = {
  SOLO: PersonIcon,
  COUPLE: HeartIcon,
  FRIENDS: FriendsIcon,
  FAMILY_WITH_KIDS: ChildIcon,
  FAMILY_WITH_PARENTS: ElderIcon,
  GROUP: GroupIcon,
};

export default function CompanionStep({ value, onSelect }) {
  return (
    <div className={styles.grid}>
      {COMPANIONS.map((companion) => {
        const Icon = COMPANION_ICONS[companion.value];
        return (
          <SelectableCard
            key={companion.value}
            className={styles.card}
            selected={companion.value === value}
            onClick={() => onSelect(companion.value)}
          >
            {Icon && <Icon size={28} className={styles.icon} />}
            <span>{companion.label}</span>
          </SelectableCard>
        );
      })}
    </div>
  );
}
