import {
  formatDateRange,
  formatDateWithWeekday,
  formatShortDate,
  formatTripLength,
} from './tripAnswerFormat';

describe('tripAnswerFormat', () => {
  it('날짜를 짧은 형식과 요일 포함 형식으로 바꾼다', () => {
    expect(formatShortDate('2026-11-01')).toBe('11/1');
    expect(formatDateWithWeekday('2026-11-01')).toBe('11월 1일 (일)');
  });

  it('기간을 N박 N+1일 / 당일치기로 표시한다', () => {
    expect(formatTripLength('2026-11-01', '2026-11-03')).toBe('2박 3일');
    expect(formatTripLength('2026-10-31', '2026-11-01')).toBe('1박 2일');
    expect(formatTripLength('2026-11-01', '2026-11-01')).toBe('당일치기');
    expect(formatTripLength('2026-11-01', null)).toBeNull();
  });

  it('칩용 날짜 범위 문구를 만든다', () => {
    expect(formatDateRange('2026-11-01', '2026-11-03')).toBe('11/1~11/3 · 2박 3일');
    expect(formatDateRange('2026-11-01', '2026-11-01')).toBe('11/1 · 당일치기');
  });
});
