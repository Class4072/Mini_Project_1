import { useId } from 'react';
import SelectableCard from '../../../components/SelectableCard/SelectableCard';
import {
  MAX_THEMES,
  PLACES_PER_DAY,
  START_TIMES,
  THEMES,
} from '../../../features/trip-request/tripRequestOptions';
import styles from './OptionalStep.module.css';

function OptionGroup({ title, hint, children }) {
  const titleId = useId();
  return (
    <div role="group" aria-labelledby={titleId} className={styles.group}>
      <div className={styles.groupHeader}>
        <h3 id={titleId} className={styles.groupTitle}>
          {title}
        </h3>
        {hint && <span className={styles.hint}>{hint}</span>}
      </div>
      {children}
    </div>
  );
}

// 위 큰 글자 + 아래 작은 글자 3열 버튼
function TwoLineOptions({ options, value, onSelect }) {
  return (
    <div className={styles.twoLineOptions}>
      {options.map((option) => (
        <SelectableCard
          key={option.value}
          className={styles.twoLineOption}
          selected={option.value === value}
          onClick={() => onSelect(option.value)}
        >
          <span className={styles.primaryText}>{option.primaryText}</span>
          <span className={styles.secondaryText}>{option.secondaryText}</span>
        </SelectableCard>
      ))}
    </div>
  );
}

const PLACES_OPTIONS = PLACES_PER_DAY.map((o) => ({
  value: o.value,
  primaryText: o.description,
  secondaryText: o.label,
}));

const START_TIME_OPTIONS = START_TIMES.map((o) => ({
  value: o.value,
  primaryText: o.time,
  secondaryText: o.note ? `${o.label} · ${o.note}` : o.label,
}));

export default function OptionalStep({
  themes,
  placesPerDay,
  startTime,
  onToggleTheme,
  onClearThemes,
  onSelectPlacesPerDay,
  onSelectStartTime,
}) {
  const isThemeFull = themes.length >= MAX_THEMES;

  return (
    <div className={styles.optional}>
      <OptionGroup title="어떤 여행을 좋아하나요?" hint={`최대 ${MAX_THEMES}개`}>
        <div className={styles.themes}>
          {/* "골고루" = themes 빈 배열 */}
          <SelectableCard
            className={styles.theme}
            selected={themes.length === 0}
            onClick={onClearThemes}
          >
            골고루
          </SelectableCard>
          {THEMES.map((theme) => {
            const selected = themes.includes(theme.value);
            const disabled = isThemeFull && !selected;
            return (
              <SelectableCard
                key={theme.value}
                className={styles.theme}
                selected={selected}
                aria-disabled={disabled || undefined}
                onClick={() => !disabled && onToggleTheme(theme.value)}
              >
                {theme.label}
              </SelectableCard>
            );
          })}
        </div>
      </OptionGroup>

      <OptionGroup title="하루에 몇 곳 정도 가볼까요?">
        <TwoLineOptions
          options={PLACES_OPTIONS}
          value={placesPerDay}
          onSelect={onSelectPlacesPerDay}
        />
      </OptionGroup>

      <OptionGroup title="하루를 언제 시작할까요?">
        <TwoLineOptions
          options={START_TIME_OPTIONS}
          value={startTime}
          onSelect={onSelectStartTime}
        />
      </OptionGroup>
    </div>
  );
}
