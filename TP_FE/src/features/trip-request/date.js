const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

// 'YYYY-MM-DD' 형식의 KST 기준 오늘 날짜. 테스트에서는 now 를 주입한다.
export function getTodayKST(now = new Date()) {
  return new Date(now.getTime() + KST_OFFSET_MS).toISOString().slice(0, 10);
}

function toUtcTime(dateString) {
  const match = DATE_PATTERN.exec(dateString ?? "");
  if (!match) return null;
  const [, y, m, d] = match.map(Number);
  const time = Date.UTC(y, m - 1, d);
  // 2026-02-30 처럼 존재하지 않는 날짜 거르기
  return new Date(time).getUTCDate() === d ? time : null;
}

export function isValidDateString(dateString) {
  return toUtcTime(dateString) !== null;
}

// to - from (일 단위). 형식이 잘못되면 null.
export function daysBetween(from, to) {
  const a = toUtcTime(from);
  const b = toUtcTime(to);
  if (a === null || b === null) return null;
  return Math.round((b - a) / DAY_MS);
}
