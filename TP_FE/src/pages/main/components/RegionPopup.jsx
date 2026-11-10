import { useCallback, useEffect, useId, useRef } from 'react';
import CloseIcon from '../../../components/icons/CloseIcon';
import RegionGrid from './RegionGrid';
import styles from './RegionPopup.module.css';

// 질문 패널 안에 뜨는 지역 바꾸기 팝업. triggerRef 는 팝업을 연 지역 칩.
// X·Esc·지역 선택으로 닫으면 칩으로 포커스를 돌려주고, 바깥 클릭으로 닫을 때는 그대로 둔다.
export default function RegionPopup({ id, regionCode, triggerRef, onSelect, onClose }) {
  const popupRef = useRef(null);
  const titleId = useId();

  const closeAndRestoreFocus = useCallback(() => {
    onClose();
    triggerRef.current?.focus();
  }, [onClose, triggerRef]);

  useEffect(() => {
    popupRef.current.querySelector('[aria-pressed="true"]')?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') closeAndRestoreFocus();
    };
    const handleMouseDown = (event) => {
      // 칩 클릭은 칩의 onClick 이 열고 닫기를 처리한다.
      if (popupRef.current.contains(event.target)) return;
      if (triggerRef.current?.contains(event.target)) return;
      onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleMouseDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, [closeAndRestoreFocus, onClose, triggerRef]);

  const handleSelect = (code) => {
    if (code !== regionCode) onSelect(code);
    closeAndRestoreFocus();
  };

  return (
    <div ref={popupRef} id={id} role="dialog" aria-labelledby={titleId} className={styles.popup}>
      <div className={styles.header}>
        <h2 id={titleId} className={styles.title}>
          지역 바꾸기
        </h2>
        <button
          type="button"
          className={styles.closeButton}
          aria-label="닫기"
          onClick={closeAndRestoreFocus}
        >
          <CloseIcon size={18} />
        </button>
      </div>
      <RegionGrid selectedCode={regionCode} onSelect={handleSelect} compact />
      <p className={styles.note}>지역을 바꿔도 지금까지 고른 답은 그대로 남아요.</p>
    </div>
  );
}
