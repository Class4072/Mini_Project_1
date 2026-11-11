import MinusIcon from "../../../components/icons/MinusIcon";
import PlusIcon from "../../../components/icons/PlusIcon";
import SelectableCard from "../../../components/SelectableCard/SelectableCard";
import {
  MAX_TRAVELERS,
  TRAVELER_COUNT_PRESETS,
} from "../../../features/trip-request/tripRequestOptions";
import styles from "./TravelerCountStep.module.css";

// 마지막 프리셋("6명 이상")부터는 아래 조절 박스로 인원을 맞춘다.
const STEPPER_MIN = TRAVELER_COUNT_PRESETS.at(-1).value;

// maxTravelers 는 테스트에서 상한을 바꿔 검증하기 위한 인자.
export default function TravelerCountStep({ value, onChange, maxTravelers = MAX_TRAVELERS }) {
  const isStepperActive = value >= STEPPER_MIN;
  const stepperClassName = [styles.stepper, !isStepperActive && styles.inactive]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={styles.travelerCount}>
      <div className={styles.presets}>
        {TRAVELER_COUNT_PRESETS.map((preset) => {
          const selected = preset.value === STEPPER_MIN ? isStepperActive : preset.value === value;
          return (
            <SelectableCard
              key={preset.value}
              className={styles.preset}
              selected={selected}
              // 이미 6명 이상이면 조절해 둔 인원을 유지한다.
              onClick={() => !selected && onChange(preset.value)}
            >
              {preset.label}
            </SelectableCard>
          );
        })}
      </div>

      <div className={stepperClassName}>
        <span className={styles.stepperText}>
          {STEPPER_MIN}명 이상을 고르면 여기서 인원을 맞춰요
        </span>
        <div className={styles.controls}>
          <button
            type="button"
            className={styles.stepperButton}
            aria-label="인원 줄이기"
            disabled={!isStepperActive || value <= STEPPER_MIN}
            onClick={() => onChange(value - 1)}
          >
            <MinusIcon size={18} />
          </button>
          <span className={styles.count} aria-live="polite">
            {value}명
          </span>
          <button
            type="button"
            className={styles.stepperButton}
            aria-label="인원 늘리기"
            disabled={!isStepperActive || (maxTravelers !== null && value >= maxTravelers)}
            onClick={() => onChange(value + 1)}
          >
            <PlusIcon size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
