import {
  DEFAULT_PLACES_PER_DAY,
  DEFAULT_START_TIME,
  MAX_THEMES,
  REQUIRED_STEPS,
  SOLO,
} from './tripRequestOptions';
import { canProceed, getVisibleSteps } from './tripRequestSelectors';

export const initialTripRequestState = {
  regionCode: null,
  startDate: null,
  endDate: null,
  companionType: null,
  travelerCount: null,
  transport: null,
  themes: [],
  placesPerDay: DEFAULT_PLACES_PER_DAY,
  startTime: DEFAULT_START_TIME,
  currentStep: 'region',
};

export const TRIP_REQUEST_ACTIONS = {
  SELECT_REGION: 'SELECT_REGION',
  SET_DATES: 'SET_DATES',
  SELECT_COMPANION: 'SELECT_COMPANION',
  SET_TRAVELER_COUNT: 'SET_TRAVELER_COUNT',
  SELECT_TRANSPORT: 'SELECT_TRANSPORT',
  TOGGLE_THEME: 'TOGGLE_THEME',
  CLEAR_THEMES: 'CLEAR_THEMES',
  SET_PLACES_PER_DAY: 'SET_PLACES_PER_DAY',
  SET_START_TIME: 'SET_START_TIME',
  NEXT: 'NEXT',
  PREV: 'PREV',
  GO_TO_STEP: 'GO_TO_STEP',
};

const A = TRIP_REQUEST_ACTIONS;

function selectCompanion(state, companionType) {
  if (companionType === SOLO) {
    return { ...state, companionType, travelerCount: 1 };
  }
  // 인원이 비어 있거나 SOLO 의 1명이면 2명으로 채우고, 그 외에는 기존 인원 유지
  const travelerCount =
    state.travelerCount === null || state.travelerCount === 1 ? 2 : state.travelerCount;
  return { ...state, companionType, travelerCount };
}

function toggleTheme(state, theme) {
  if (state.themes.includes(theme)) {
    return { ...state, themes: state.themes.filter((t) => t !== theme) };
  }
  if (state.themes.length >= MAX_THEMES) return state;
  return { ...state, themes: [...state.themes, theme] };
}

function moveBy(state, offset) {
  const steps = getVisibleSteps(state);
  const nextStep = steps[steps.indexOf(state.currentStep) + offset];
  return nextStep ? { ...state, currentStep: nextStep } : state;
}

// today('YYYY-MM-DD')는 NEXT 의 날짜 검증용. 훅에서 주입한다.
export function tripRequestReducer(state, action) {
  switch (action.type) {
    case A.SELECT_REGION:
      return {
        ...state,
        regionCode: action.regionCode,
        // 첫 화면에서만 다음 단계로 이동, 그 외(지역 칩 팝업)에서는 단계 유지
        currentStep: state.currentStep === 'region' ? 'date' : state.currentStep,
      };
    case A.SET_DATES:
      return { ...state, startDate: action.startDate, endDate: action.endDate };
    case A.SELECT_COMPANION:
      return selectCompanion(state, action.companionType);
    case A.SET_TRAVELER_COUNT:
      return { ...state, travelerCount: action.travelerCount };
    case A.SELECT_TRANSPORT:
      return { ...state, transport: action.transport };
    case A.TOGGLE_THEME:
      return toggleTheme(state, action.theme);
    case A.CLEAR_THEMES:
      return { ...state, themes: [] };
    case A.SET_PLACES_PER_DAY:
      return { ...state, placesPerDay: action.placesPerDay };
    case A.SET_START_TIME:
      return { ...state, startTime: action.startTime };
    case A.NEXT:
      if (!REQUIRED_STEPS.includes(state.currentStep)) return state;
      if (!canProceed(state, { today: action.today })) return state;
      return moveBy(state, 1);
    case A.PREV:
      // date 이전(region)으로는 돌아가지 않는다.
      if (state.currentStep === 'date' || state.currentStep === 'region') return state;
      return moveBy(state, -1);
    case A.GO_TO_STEP:
      if (!REQUIRED_STEPS.includes(action.step)) return state;
      if (!getVisibleSteps(state).includes(action.step)) return state;
      return { ...state, currentStep: action.step };
    default:
      return state;
  }
}
