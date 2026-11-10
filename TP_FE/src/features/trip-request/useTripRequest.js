import { useMemo, useReducer } from "react";
import { getTodayKST } from "./date";
import { toTripRequest } from "./toTripRequest";
import {
  initialTripRequestState,
  TRIP_REQUEST_ACTIONS as A,
  tripRequestReducer,
} from "./tripRequestReducer";
import { canProceed, canSubmit, getProgress, getVisibleSteps } from "./tripRequestSelectors";

// getToday 는 테스트에서 오늘 날짜를 고정하기 위한 주입 지점.
export function useTripRequest({
  getToday = getTodayKST,
  initialState = initialTripRequestState,
} = {}) {
  const [state, dispatch] = useReducer(tripRequestReducer, initialState);
  const today = getToday();

  const actions = useMemo(
    () => ({
      selectRegion: (regionCode) => dispatch({ type: A.SELECT_REGION, regionCode }),
      setDates: (startDate, endDate) => dispatch({ type: A.SET_DATES, startDate, endDate }),
      selectCompanion: (companionType) => dispatch({ type: A.SELECT_COMPANION, companionType }),
      setTravelerCount: (travelerCount) => dispatch({ type: A.SET_TRAVELER_COUNT, travelerCount }),
      selectTransport: (transport) => dispatch({ type: A.SELECT_TRANSPORT, transport }),
      toggleTheme: (theme) => dispatch({ type: A.TOGGLE_THEME, theme }),
      clearThemes: () => dispatch({ type: A.CLEAR_THEMES }),
      setPlacesPerDay: (placesPerDay) => dispatch({ type: A.SET_PLACES_PER_DAY, placesPerDay }),
      setStartTime: (startTime) => dispatch({ type: A.SET_START_TIME, startTime }),
      next: () => dispatch({ type: A.NEXT, today: getToday() }),
      prev: () => dispatch({ type: A.PREV }),
      goToStep: (step) => dispatch({ type: A.GO_TO_STEP, step }),
    }),
    [getToday],
  );

  return {
    state,
    actions,
    today,
    visibleSteps: getVisibleSteps(state),
    progress: getProgress(state),
    canGoNext: canProceed(state, { today }),
    canSubmit: canSubmit(state, { today }),
    requestBody: toTripRequest(state),
  };
}
