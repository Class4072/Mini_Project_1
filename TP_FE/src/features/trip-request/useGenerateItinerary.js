import { useCallback, useRef, useState } from "react";
import { generateItinerary } from "./tripRequestApi";

export const GENERATE_ERROR_MESSAGES = {
  timeout: "일정 만들기가 오래 걸려 멈췄어요. 잠시 후 다시 시도해주세요.",
  default: "일정을 만들지 못했어요. 잠시 후 다시 시도해주세요.",
};

function toErrorMessage(error) {
  // axios 타임아웃: 기본은 ECONNABORTED, transitional.clarifyTimeoutError 설정 시 ETIMEDOUT
  const isTimeout = error?.code === "ECONNABORTED" || error?.code === "ETIMEDOUT";
  return isTimeout ? GENERATE_ERROR_MESSAGES.timeout : GENERATE_ERROR_MESSAGES.default;
}

// status: 'idle' | 'submitting' | 'error'
// submit(requestBody) → 성공 시 itineraryId(onSuccess 도 호출), 실패·중복 호출 시 null
export function useGenerateItinerary({ onSuccess } = {}) {
  const [status, setStatus] = useState("idle");
  const [errorMessage, setErrorMessage] = useState(null);
  // 같은 틱의 연속 클릭은 state 로 막을 수 없어 ref 로 막는다.
  const isSubmittingRef = useRef(false);

  const submit = useCallback(
    async (requestBody) => {
      if (isSubmittingRef.current) return null;
      isSubmittingRef.current = true;
      setStatus("submitting");
      setErrorMessage(null);

      let itineraryId;
      try {
        ({ itineraryId } = await generateItinerary(requestBody));
      } catch (error) {
        setStatus("error");
        setErrorMessage(toErrorMessage(error));
        return null;
      } finally {
        isSubmittingRef.current = false;
      }

      setStatus("idle");
      onSuccess?.(itineraryId);
      return itineraryId;
    },
    [onSuccess],
  );

  return { status, errorMessage, submit };
}
