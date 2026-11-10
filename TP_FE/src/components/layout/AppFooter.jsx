import styles from "./AppFooter.module.css";

export default function AppFooter() {
  return (
    <footer className={styles.footer}>
      <nav className={styles.links}>
        <a href="#" className={styles.brand}>
          TP
        </a>
        <a href="#">이용약관</a>
        <a href="#">개인정보처리방침</a>
      </nav>
      <p className={styles.credit}>관광 정보: 한국관광공사 · 지도: 카카오맵</p>
    </footer>
  );
}
