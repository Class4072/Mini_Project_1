import { daysBetween, getTodayKST, isValidDateString } from './date';
import {
  MAX_DAYS_AHEAD,
  MAX_TRAVELERS,
  MAX_TRIP_DAYS,
  REQUIRED_STEPS,
  SOLO,
  STEPS,
} from './tripRequestOptions';

// limits 는 테스트에서 제약 상수를 바꿔 검증하기 위한 인자. 기본값은 tripRequestOptions 상수.
export function isDateRangeValid(
  { startDate, endDate },
  { today = getTodayKST(), maxTripDays = MAX_TRIP_DAYS, maxDaysAhead = MAX_DAYS_AHEAD } = {},
) {
  if (!isValidDateString(startDate) || !isValidDateString(endDate)) return false;

  const tripLength = daysBetween(startDate, endDate);
  const daysAhead = daysBetween(today, startDate);
  if (tripLength < 0 || daysAhead === null || daysAhead < 0) return false;
  if (maxTripDays !== null && tripLength + 1 > maxTripDays) return false;
  if (maxDaysAhead !== null && daysAhead > maxDaysAhead) return false;
  return true;
}

export function isTravelerCountValid(travelerCount, { maxTravelers = MAX_TRAVELERS } = {}) {
  if (!Number.isInteger(travelerCount) || travelerCount < 2) return false;
  return maxTravelers === null || travelerCount <= maxTravelers;
}

export function isStepValid(state, step, limits) {
  switch (step) {
    case 'region':
      return state.regionCode !== null;
    case 'date':
      return isDateRangeValid(state, limits);
    case 'companion':
      return state.companionType !== null;
    case 'travelerCount':
      return state.companionType === SOLO || isTravelerCountValid(state.travelerCount, limits);
    case 'transport':
      return state.transport !== null;
    default:
      return true;
  }
}

// 현재 단계의 다음 버튼 활성 여부
export function canProceed(state, limits) {
  return isStepValid(state, state.currentStep, limits);
}

// 일정 만들기 버튼 활성 여부: 지역 + 모든 필수 답이 유효
export function canSubmit(state, limits) {
  return getVisibleSteps(state).every((step) => isStepValid(state, step, limits));
}

// SOLO 면 travelerCount 단계를 건너뛴다.
export function getVisibleSteps(state) {
  return state.companionType === SOLO ? STEPS.filter((s) => s !== 'travelerCount') : STEPS;
}

export function getVisibleRequiredSteps(state) {
  return getVisibleSteps(state).filter((s) => REQUIRED_STEPS.includes(s));
}

// { current, total }. region 단계는 진행 표시 없음(null), optional 단계는 필수 질문을 모두 마친 상태(total/total).
export function getProgress(state) {
  const requiredSteps = getVisibleRequiredSteps(state);
  const total = requiredSteps.length;
  if (state.currentStep === 'region') return null;
  if (state.currentStep === 'optional') return { current: total, total };
  return { current: requiredSteps.indexOf(state.currentStep) + 1, total };
}
