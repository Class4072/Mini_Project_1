import { initialTripRequestState } from './tripRequestReducer';
import {
  canProceed,
  canSubmit,
  getProgress,
  getVisibleSteps,
  isDateRangeValid,
  isTravelerCountValid,
} from './tripRequestSelectors';

const TODAY = '2026-10-20';
const at = (currentStep, overrides = {}) => ({
  ...initialTripRequestState,
  currentStep,
  ...overrides,
});

describe('isDateRangeValid (오늘 = 2026-10-20 고정)', () => {
  const valid = (startDate, endDate, limits = {}) =>
    isDateRangeValid({ startDate, endDate }, { today: TODAY, ...limits });

  it('출발일·도착일이 모두 있어야 한다', () => {
    expect(valid(null, null)).toBe(false);
    expect(valid('2026-10-21', null)).toBe(false);
    expect(valid(null, '2026-10-21')).toBe(false);
  });

  it('오늘 출발·당일치기는 허용한다', () => {
    expect(valid('2026-10-20', '2026-10-20')).toBe(true);
  });

  it('과거 출발일은 거부한다', () => {
    expect(valid('2026-10-19', '2026-10-22')).toBe(false);
  });

  it('도착일이 출발일보다 빠르면 거부한다', () => {
    expect(valid('2026-10-25', '2026-10-24')).toBe(false);
  });

  it('월 경계를 넘는 기간을 허용한다', () => {
    expect(valid('2026-10-31', '2026-11-02')).toBe(true);
    expect(valid('2026-11-01', '2026-10-31')).toBe(false);
  });

  it('제약 상수가 null 이면 기간·출발일 제한을 검사하지 않는다', () => {
    expect(valid('2027-12-01', '2028-01-31')).toBe(true);
  });

  it('maxTripDays 는 출발일·도착일 포함 일수로 검사한다', () => {
    // 10/31~11/02 = 3일
    expect(valid('2026-10-31', '2026-11-02', { maxTripDays: 3 })).toBe(true);
    expect(valid('2026-10-31', '2026-11-02', { maxTripDays: 2 })).toBe(false);
  });

  it('maxDaysAhead 는 오늘부터 출발일까지 일수로 검사한다', () => {
    // 10/20 → 11/19 = 30일
    expect(valid('2026-11-19', '2026-11-20', { maxDaysAhead: 30 })).toBe(true);
    expect(valid('2026-11-20', '2026-11-21', { maxDaysAhead: 30 })).toBe(false);
  });
});

describe('isTravelerCountValid', () => {
  it('2 이상의 정수만 허용한다', () => {
    expect(isTravelerCountValid(2)).toBe(true);
    expect(isTravelerCountValid(30)).toBe(true);
    expect(isTravelerCountValid(1)).toBe(false);
    expect(isTravelerCountValid(2.5)).toBe(false);
    expect(isTravelerCountValid('3')).toBe(false);
    expect(isTravelerCountValid(null)).toBe(false);
  });

  it('maxTravelers 가 있으면 그 이하만 허용한다', () => {
    expect(isTravelerCountValid(10, { maxTravelers: 10 })).toBe(true);
    expect(isTravelerCountValid(11, { maxTravelers: 10 })).toBe(false);
  });
});

describe('canProceed (규칙 2)', () => {
  const limits = { today: TODAY };

  it('date: 날짜 범위가 유효해야 한다', () => {
    expect(canProceed(at('date'), limits)).toBe(false);
    expect(canProceed(at('date', { startDate: TODAY, endDate: '2026-10-22' }), limits)).toBe(true);
    expect(canProceed(at('date', { startDate: '2026-10-19', endDate: '2026-10-22' }), limits)).toBe(
      false,
    );
  });

  it('companion: 선택돼야 한다', () => {
    expect(canProceed(at('companion'), limits)).toBe(false);
    expect(canProceed(at('companion', { companionType: 'FRIENDS' }), limits)).toBe(true);
  });

  it('travelerCount: 2 이상의 정수여야 한다', () => {
    const state = { companionType: 'FRIENDS' };
    expect(canProceed(at('travelerCount', { ...state, travelerCount: null }), limits)).toBe(false);
    expect(canProceed(at('travelerCount', { ...state, travelerCount: 1 }), limits)).toBe(false);
    expect(canProceed(at('travelerCount', { ...state, travelerCount: 7 }), limits)).toBe(true);
  });

  it('transport: 선택돼야 한다', () => {
    expect(canProceed(at('transport'), limits)).toBe(false);
    expect(canProceed(at('transport', { transport: 'WALK' }), limits)).toBe(true);
  });
});

describe('canSubmit', () => {
  const complete = {
    regionCode: '39',
    startDate: '2026-10-31',
    endDate: '2026-11-02',
    companionType: 'COUPLE',
    travelerCount: 2,
    transport: 'CAR',
  };

  it('지역과 필수 답이 모두 유효하면 true', () => {
    expect(canSubmit(at('optional', complete), { today: TODAY })).toBe(true);
    expect(canSubmit(at('optional', { ...complete, transport: null }), { today: TODAY })).toBe(
      false,
    );
  });

  it('SOLO 는 인원 검사를 하지 않는다', () => {
    const solo = { ...complete, companionType: 'SOLO', travelerCount: 1 };
    expect(canSubmit(at('optional', solo), { today: TODAY })).toBe(true);
  });
});

describe('getVisibleSteps (규칙 3)', () => {
  it('SOLO 면 travelerCount 단계가 빠진다', () => {
    expect(getVisibleSteps(at('companion', { companionType: 'SOLO' }))).toEqual([
      'region',
      'date',
      'companion',
      'transport',
      'optional',
    ]);
    expect(getVisibleSteps(at('companion', { companionType: 'GROUP' }))).toContain('travelerCount');
  });
});

describe('getProgress (규칙 7)', () => {
  it('SOLO 가 아니면 전체 4개', () => {
    expect(getProgress(at('date'))).toEqual({ current: 1, total: 4 });
    expect(getProgress(at('travelerCount', { companionType: 'FAMILY_WITH_KIDS' }))).toEqual({
      current: 3,
      total: 4,
    });
    expect(getProgress(at('transport', { companionType: 'FRIENDS' }))).toEqual({
      current: 4,
      total: 4,
    });
  });

  it('SOLO 면 전체 3개', () => {
    expect(getProgress(at('companion', { companionType: 'SOLO' }))).toEqual({
      current: 2,
      total: 3,
    });
    expect(getProgress(at('transport', { companionType: 'SOLO' }))).toEqual({
      current: 3,
      total: 3,
    });
  });

  it('region 단계는 null, optional 단계는 전체/전체', () => {
    expect(getProgress(at('region'))).toBeNull();
    expect(getProgress(at('optional', { companionType: 'SOLO' }))).toEqual({
      current: 3,
      total: 3,
    });
  });
});
