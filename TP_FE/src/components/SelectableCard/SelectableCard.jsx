import styles from './SelectableCard.module.css';

// 선택 상태를 aria-pressed 로 표시하는 버튼. 크기·배치·글자는 className 으로 덧붙인다.
export default function SelectableCard({ selected = false, className, children, ...props }) {
  return (
    <button
      type="button"
      className={[styles.card, className].filter(Boolean).join(' ')}
      aria-pressed={selected}
      {...props}
    >
      {children}
    </button>
  );
}
