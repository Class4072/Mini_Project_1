import Button from "../../../components/Button/Button";
import styles from "./QuestionPanel.module.css";

// 질문 단계 공통 틀. onPrev 가 없으면 이전 버튼을 숨긴다.
// footer 를 주면 기본 아래쪽(강조 문구 + 이전·다음) 대신 그것을 보여준다. overlay 는 패널 기준 팝업 자리.
// disabled 면 칩·선택지(footer 제외)를 fieldset 으로 한꺼번에 비활성화한다.
export default function QuestionPanel({
  chips,
  progress,
  title,
  description,
  highlight,
  onPrev,
  onNext,
  nextDisabled,
  footer,
  overlay,
  disabled = false,
  children,
}) {
  return (
    <section className={styles.panel}>
      <fieldset className={styles.content} disabled={disabled}>
        <div className={styles.top}>
          {chips}
          {progress}
        </div>

        {title && (
          <div className={styles.heading}>
            <h2 className={styles.title}>{title}</h2>
            {description && <p className={styles.description}>{description}</p>}
          </div>
        )}

        <div className={styles.body}>{children}</div>
      </fieldset>

      {footer ?? (
        <div className={styles.footer}>
          <span className={styles.highlight}>{highlight}</span>
          <div className={styles.actions}>
            {onPrev && (
              <Button variant="secondary" onClick={onPrev}>
                이전
              </Button>
            )}
            <Button className={styles.nextButton} disabled={nextDisabled} onClick={onNext}>
              다음
            </Button>
          </div>
        </div>
      )}

      {overlay}
    </section>
  );
}
