import { Outlet, useLocation } from "react-router-dom";
import ErrorBoundary from "../ErrorBoundary/ErrorBoundary";
import AppFooter from "./AppFooter";
import AppHeader from "./AppHeader";
import styles from "./AppLayout.module.css";

export default function AppLayout() {
  const { pathname } = useLocation();

  return (
    <div className={styles.layout}>
      <AppHeader />
      <div className={styles.content}>
        {/* 페이지 오류가 나도 헤더·푸터는 남기고, 다른 경로로 이동하면 초기화한다. */}
        <ErrorBoundary resetKeys={[pathname]}>
          <Outlet />
        </ErrorBoundary>
      </div>
      <AppFooter />
    </div>
  );
}
