import Chip from "../../../components/Chip/Chip";
import PencilIcon from "../../../components/icons/PencilIcon";
import {
  COMPANIONS,
  REGIONS,
  SOLO,
  TRANSPORTS,
} from "../../../features/trip-request/tripRequestOptions";
import { formatDateRange } from "../tripAnswerFormat";
import styles from "./AnsweredChips.module.css";

const labelOf = (options, value) => options.find((o) => o.value === value)?.label;

function companionLabel(state, answeredSteps) {
  if (state.companionType === SOLO) return labelOf(COMPANIONS, SOLO);
  const label = labelOf(COMPANIONS, state.companionType);
  return answeredSteps.includes("travelerCount") ? `${label} ${state.travelerCount}명` : label;
}

// 현재 단계보다 앞의 단계(= 답한 단계)만 순서대로 칩으로 보여준다.
// 지역 칩은 단계 이동 대신 지역 바꾸기 팝업을 연다.
export default function AnsweredChips({
  state,
  visibleSteps,
  onGoToStep,
  regionChipRef,
  regionPopupId,
  isRegionPopupOpen,
  onRegionClick,
}) {
  const answeredSteps = visibleSteps.slice(0, visibleSteps.indexOf(state.currentStep));

  const chips = [];
  if (answeredSteps.includes("region")) {
    chips.push({
      key: "region",
      label: labelOf(REGIONS, state.regionCode),
      props: {
        ref: regionChipRef,
        "aria-haspopup": "dialog",
        "aria-expanded": isRegionPopupOpen,
        "aria-controls": isRegionPopupOpen ? regionPopupId : undefined,
        onClick: onRegionClick,
      },
    });
  }
  if (answeredSteps.includes("date")) {
    chips.push({
      key: "date",
      label: formatDateRange(state.startDate, state.endDate),
      props: { onClick: () => onGoToStep("date") },
    });
  }
  if (answeredSteps.includes("companion")) {
    chips.push({
      key: "companion",
      label: companionLabel(state, answeredSteps),
      props: { onClick: () => onGoToStep("companion") },
    });
  }
  if (answeredSteps.includes("transport")) {
    chips.push({
      key: "transport",
      label: labelOf(TRANSPORTS, state.transport),
      props: { onClick: () => onGoToStep("transport") },
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className={styles.chips}>
      {chips.map((chip) => (
        <Chip key={chip.key} icon={<PencilIcon size={14} />} {...chip.props}>
          {chip.label}
        </Chip>
      ))}
    </div>
  );
}
