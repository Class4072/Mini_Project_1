import { daysBetween } from '../../features/trip-request/date';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

function parse(dateString) {
  const [year, month, day] = dateString.split('-').map(Number);
  return { year, month, day, weekday: new Date(Date.UTC(year, month - 1, day)).getUTCDay() };
}

// '2026-11-01' → '11/1'
export function formatShortDate(dateString) {
  const { month, day } = parse(dateString);
  return `${month}/${day}`;
}

// '2026-11-01' → '11월 1일 (일)'
export function formatDateWithWeekday(dateString) {
  const { month, day, weekday } = parse(dateString);
  return `${month}월 ${day}일 (${WEEKDAYS[weekday]})`;
}

// '2박 3일' / '당일치기'. 날짜가 비었거나 잘못되면 null.
export function formatTripLength(startDate, endDate) {
  const nights = daysBetween(startDate, endDate);
  if (nights === null || nights < 0) return null;
  return nights === 0 ? '당일치기' : `${nights}박 ${nights + 1}일`;
}

// '11/1~11/3 · 2박 3일' / '11/1 · 당일치기'
export function formatDateRange(startDate, endDate) {
  const length = formatTripLength(startDate, endDate);
  if (length === null) return null;
  const range =
    startDate === endDate
      ? formatShortDate(startDate)
      : `${formatShortDate(startDate)}~${formatShortDate(endDate)}`;
  return `${range} · ${length}`;
}
