import DateRangeCalendar from "../../../components/DateRangeCalendar/DateRangeCalendar";
import { formatDateWithWeekday } from "../tripAnswerFormat";
import styles from "./DateStep.module.css";

function DateField({ label, value }) {
  return (
    <div className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      {value ? (
        <span className={styles.fieldValue}>{formatDateWithWeekday(value)}</span>
      ) : (
        <span className={`${styles.fieldValue} ${styles.placeholder}`}>선택해주세요</span>
      )}
    </div>
  );
}

export default function DateStep({ startDate, endDate, today, onChange }) {
  return (
    <div className={styles.date}>
      <div className={styles.fields}>
        <DateField label="출발일" value={startDate} />
        <DateField label="도착일" value={endDate} />
      </div>
      <DateRangeCalendar
        startDate={startDate}
        endDate={endDate}
        minDate={today}
        onChange={onChange}
      />
    </div>
  );
}
