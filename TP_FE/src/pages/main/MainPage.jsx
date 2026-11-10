import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import RegionMap from '../../features/map/RegionMap';
import { REGIONS } from '../../features/trip-request/tripRequestOptions';
import { useGenerateItinerary } from '../../features/trip-request/useGenerateItinerary';
import { useTripRequest } from '../../features/trip-request/useTripRequest';
import RegionStep from './components/RegionStep';
import TripQuestionFlow from './components/TripQuestionFlow';
import styles from './MainPage.module.css';

const MAP_REGIONS = REGIONS.map((region) => ({ code: region.value, name: region.label }));

export default function MainPage() {
  const trip = useTripRequest();
  const navigate = useNavigate();
  const handleSuccess = useCallback(
    (itineraryId) => navigate(`/itinerary/${encodeURIComponent(itineraryId)}`),
    [navigate],
  );
  const generate = useGenerateItinerary({ onSuccess: handleSuccess });

  // 오류 문구는 제출한 답 그대로일 때만 보여준다. (답을 바꾸면 state 가 바뀌어 사라짐)
  const [submittedState, setSubmittedState] = useState(null);
  const submitError =
    generate.status === 'error' && submittedState === trip.state ? generate.errorMessage : null;

  const handleSubmit = (requestBody) => {
    setSubmittedState(trip.state);
    generate.submit(requestBody);
  };

  return (
    <main className={styles.section}>
      <div className={styles.grid}>
        <div className={styles.panel}>
          {trip.state.currentStep === 'region' ? (
            <RegionStep regionCode={trip.state.regionCode} onSelect={trip.actions.selectRegion} />
          ) : (
            <TripQuestionFlow
              trip={trip}
              onSubmit={handleSubmit}
              isSubmitting={generate.status === 'submitting'}
              submitError={submitError}
            />
          )}
        </div>
        <div className={styles.map}>
          <RegionMap
            regions={MAP_REGIONS}
            selectedRegionCode={trip.state.regionCode}
            onSelectRegion={trip.actions.selectRegion}
          />
        </div>
      </div>
    </main>
  );
}
