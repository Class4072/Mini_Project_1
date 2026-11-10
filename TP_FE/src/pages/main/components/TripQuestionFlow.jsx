import { useCallback, useId, useRef, useState } from 'react';
import Button from '../../../components/Button/Button';
import StepProgress from '../../../components/StepProgress/StepProgress';
import { formatTripLength } from '../tripAnswerFormat';
import AnsweredChips from './AnsweredChips';
import CompanionStep from './CompanionStep';
import DateStep from './DateStep';
import OptionalStep from './OptionalStep';
import QuestionPanel from './QuestionPanel';
import RegionPopup from './RegionPopup';
import TransportStep from './TransportStep';
import TravelerCountStep from './TravelerCountStep';
import styles from './TripQuestionFlow.module.css';

const STEP_TEXT = {
  date: { title: '언제 가나요?', description: '출발일과 도착일을 차례로 눌러주세요.' },
  companion: {
    title: '누구와 가나요?',
    description: '함께 가는 사람에 맞춰 장소와 동선을 골라요.',
  },
  travelerCount: { title: '몇 명이 가나요?', description: '나를 포함한 전체 인원이에요.' },
  transport: {
    title: '무엇으로 이동하나요?',
    description: '이동 수단에 따라 동선과 이동 시간이 달라져요.',
  },
  optional: { title: '원하는 여행 스타일이 있나요?', description: '바꾸고 싶은 것만 고르세요.' },
};

function StepBody({ state, actions, today }) {
  switch (state.currentStep) {
    case 'date':
      return (
        <DateStep
          startDate={state.startDate}
          endDate={state.endDate}
          today={today}
          onChange={actions.setDates}
        />
      );
    case 'companion':
      return <CompanionStep value={state.companionType} onSelect={actions.selectCompanion} />;
    case 'travelerCount':
      return <TravelerCountStep value={state.travelerCount} onChange={actions.setTravelerCount} />;
    case 'transport':
      return <TransportStep value={state.transport} onSelect={actions.selectTransport} />;
    case 'optional':
      return (
        <OptionalStep
          themes={state.themes}
          placesPerDay={state.placesPerDay}
          startTime={state.startTime}
          onToggleTheme={actions.toggleTheme}
          onClearThemes={actions.clearThemes}
          onSelectPlacesPerDay={actions.setPlacesPerDay}
          onSelectStartTime={actions.setStartTime}
        />
      );
    default:
      return null;
  }
}

// region 이외 단계의 질문 패널. 상태·규칙은 모두 useTripRequest 결과를 그대로 쓴다.
// onSubmit(requestBody) 이 없으면 일정 만들기 버튼은 아무 동작도 하지 않는다.
// isSubmitting 이면 답을 바꿀 수 없게 막고, submitError 는 일정 만들기 버튼 위에 보여준다.
export default function TripQuestionFlow({ trip, onSubmit, isSubmitting = false, submitError }) {
  const { state, actions, today, visibleSteps, progress, canGoNext, canSubmit, requestBody } = trip;
  const { currentStep } = state;
  const isOptional = currentStep === 'optional';

  const [isRegionPopupOpen, setIsRegionPopupOpen] = useState(false);
  const regionChipRef = useRef(null);
  const regionPopupId = useId();
  const closeRegionPopup = useCallback(() => setIsRegionPopupOpen(false), []);

  const submitFooter = (
    <div className={styles.submit}>
      {submitError && (
        <p role="alert" className={styles.submitError}>
          {submitError}
        </p>
      )}
      <Button
        size="lg"
        className={styles.submitButton}
        disabled={!canSubmit || isSubmitting}
        aria-busy={isSubmitting || undefined}
        onClick={() => onSubmit?.(requestBody)}
      >
        {isSubmitting ? '만드는 중…' : '일정 만들기'}
      </Button>
      <p className={styles.submitNote}>
        {isSubmitting
          ? '잠시만 기다려 주세요. 일정을 만들고 있어요.'
          : '선택하지 않으면 기본값으로 만들어요'}
      </p>
    </div>
  );

  return (
    <QuestionPanel
      chips={
        <AnsweredChips
          state={state}
          visibleSteps={visibleSteps}
          onGoToStep={actions.goToStep}
          regionChipRef={regionChipRef}
          regionPopupId={regionPopupId}
          isRegionPopupOpen={isRegionPopupOpen}
          onRegionClick={() => setIsRegionPopupOpen((open) => !open)}
        />
      }
      progress={
        <StepProgress
          total={progress.total}
          filled={progress.current}
          label={isOptional ? '필수 완료' : `${progress.current} / ${progress.total}`}
        />
      }
      title={STEP_TEXT[currentStep]?.title}
      description={STEP_TEXT[currentStep]?.description}
      highlight={currentStep === 'date' ? formatTripLength(state.startDate, state.endDate) : null}
      onPrev={currentStep === 'date' ? null : actions.prev}
      onNext={actions.next}
      nextDisabled={!canGoNext}
      footer={isOptional ? submitFooter : null}
      disabled={isSubmitting}
      overlay={
        isRegionPopupOpen && (
          <RegionPopup
            id={regionPopupId}
            regionCode={state.regionCode}
            triggerRef={regionChipRef}
            onSelect={actions.selectRegion}
            onClose={closeRegionPopup}
          />
        )
      }
    >
      <StepBody state={state} actions={actions} today={today} />
    </QuestionPanel>
  );
}
