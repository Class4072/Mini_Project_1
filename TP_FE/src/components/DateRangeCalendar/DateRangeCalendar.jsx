import { useState } from "react";
import ChevronLeftIcon from "../icons/ChevronLeftIcon";
import ChevronRightIcon from "../icons/ChevronRightIcon";
import styles from "./DateRangeCalendar.module.css";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const pad = (n) => String(n).padStart(2, "0");
const toDateString = (year, month, day) => `${year}-${pad(month)}-${pad(day)}`;

function parseMonth(dateString) {
  const [year, month] = dateString.split("-").map(Number);
  return { year, month };
}

function addMonths({ year, month }, offset) {
  const index = year * 12 + (month - 1) + offset;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

// 날짜는 'YYYY-MM-DD' 문자열로 주고받는다. (문자열 비교 = 날짜 비교)
// minDate 이전 날짜는 고를 수 없다. 처음에는 startDate 가 있으면 그 달, 없으면 minDate 의 달을 보여준다.
export default function DateRangeCalendar({ startDate, endDate, minDate, onChange }) {
  const [view, setView] = useState(() => parseMonth(startDate ?? minDate));

  const firstWeekday = new Date(Date.UTC(view.year, view.month - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(view.year, view.month, 0)).getUTCDate();
  const minMonth = minDate ? parseMonth(minDate) : null;
  const isPrevDisabled =
    minMonth !== null && view.year * 12 + view.month <= minMonth.year * 12 + minMonth.month;

  const handleSelect = (date) => {
    if (!startDate || endDate || date < startDate) {
      onChange(date, null);
    } else {
      onChange(startDate, date);
    }
  };

  return (
    <div className={styles.calendar}>
      <div className={styles.header}>
        <button
          type="button"
          className={styles.navButton}
          aria-label="이전 달"
          disabled={isPrevDisabled}
          onClick={() => setView(addMonths(view, -1))}
        >
          <ChevronLeftIcon size={18} />
        </button>
        <span className={styles.title}>
          {view.year}년 {view.month}월
        </span>
        <button
          type="button"
          className={styles.navButton}
          aria-label="다음 달"
          onClick={() => setView(addMonths(view, 1))}
        >
          <ChevronRightIcon size={18} />
        </button>
      </div>

      <div className={styles.weekdays} aria-hidden="true">
        {WEEKDAYS.map((weekday, i) => (
          <span key={weekday} className={i === 0 ? styles.sunday : undefined}>
            {weekday}
          </span>
        ))}
      </div>

      <div className={styles.days}>
        {Array.from({ length: firstWeekday }, (_, i) => (
          <span key={`empty-${i}`} aria-hidden="true" />
        ))}
        {Array.from({ length: daysInMonth }, (_, i) => {
          const day = i + 1;
          const date = toDateString(view.year, view.month, day);
          const weekday = (firstWeekday + i) % 7;
          const isSelected = date === startDate || date === endDate;
          const isInRange = startDate && endDate && date > startDate && date < endDate;
          const className = [styles.day, isSelected && styles.selected, isInRange && styles.inRange]
            .filter(Boolean)
            .join(" ");

          return (
            <button
              key={date}
              type="button"
              className={className}
              aria-label={`${view.year}년 ${view.month}월 ${day}일 ${WEEKDAYS[weekday]}요일`}
              aria-pressed={isSelected}
              disabled={Boolean(minDate) && date < minDate}
              onClick={() => handleSelect(date)}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}
