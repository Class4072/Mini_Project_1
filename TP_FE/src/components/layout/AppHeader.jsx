import { Link } from "react-router-dom";
import Button from "../Button/Button";
import PinIcon from "../icons/PinIcon";
import styles from "./AppHeader.module.css";

export default function AppHeader() {
  return (
    <header className={styles.header}>
      <Link to="/" className={styles.logo}>
        <span className={styles.logoMark}>
          <PinIcon size={20} />
        </span>
        <span className={styles.logoText}>TP</span>
      </Link>
      {/* TODO: 로그인 기능 구현 시 연결 */}
      <Button variant="secondary" size="sm">
        로그인
      </Button>
    </header>
  );
}
