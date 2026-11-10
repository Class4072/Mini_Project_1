import RegionGrid from "./RegionGrid";
import styles from "./RegionStep.module.css";

export default function RegionStep({ regionCode, onSelect }) {
  return (
    <div className={styles.region}>
      <h1 className={styles.title}>
        어디로 떠날까요?
        <br />
        지도에서 골라보세요.
      </h1>
      <p className={styles.description}>
        지역을 고르고 몇 가지만 답하면
        <br />
        날씨와 운영시간에 맞춘 일자별 동선을 만들어 드려요.
      </p>
      <section className={styles.picker}>
        <h2 className={styles.subtitle}>지역 고르기</h2>
        <RegionGrid selectedCode={regionCode} onSelect={onSelect} />
      </section>
    </div>
  );
}
