import styles from "./Chip.module.css";

export default function Chip({ icon, className, children, ...props }) {
  return (
    <button type="button" className={[styles.chip, className].filter(Boolean).join(" ")} {...props}>
      <span>{children}</span>
      {icon && <span className={styles.icon}>{icon}</span>}
    </button>
  );
}
