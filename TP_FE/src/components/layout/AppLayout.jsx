import { Outlet } from 'react-router-dom';
import AppFooter from './AppFooter';
import AppHeader from './AppHeader';
import styles from './AppLayout.module.css';

export default function AppLayout() {
  return (
    <div className={styles.layout}>
      <AppHeader />
      <div className={styles.content}>
        <Outlet />
      </div>
      <AppFooter />
    </div>
  );
}
