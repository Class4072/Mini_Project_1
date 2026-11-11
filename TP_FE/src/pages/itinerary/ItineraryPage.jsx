import { useNavigate, useParams } from "react-router-dom";
import Button from "../../components/Button/Button";
import styles from "./ItineraryPage.module.css";

// 일정 결과 자리. 일정 편집 화면은 다음 작업에서 만든다.
export default function ItineraryPage() {
  const { itineraryId } = useParams();
  const navigate = useNavigate();

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>일정 화면은 준비 중이에요</h1>
      <p className={styles.id}>일정 ID: {itineraryId}</p>
      <Button variant="secondary" className={styles.homeButton} onClick={() => navigate("/")}>
        처음으로
      </Button>
    </main>
  );
}
