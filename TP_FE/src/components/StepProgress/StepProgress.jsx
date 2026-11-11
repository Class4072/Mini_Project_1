import styles from "./StepProgress.module.css";

// total 칸 중 filled 칸을 채우고 오른쪽에 label 을 보여준다.
export default function StepProgress({ total, filled, label }) {
  return (
    <div className={styles.progress}>
      <div className={styles.bars} aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={[styles.bar, i < filled && styles.filled].filter(Boolean).join(" ")}
          />
        ))}
      </div>
      <span className={styles.label}>{label}</span>
    </div>
  );
}
