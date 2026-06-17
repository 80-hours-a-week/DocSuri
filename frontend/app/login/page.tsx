import { Suspense } from 'react';
import styles from '../page.module.css';
import { AppHeader } from '@/components/AppHeader';
import { LoginForm } from '@/components/LoginForm';

// Login route (US-A2). LoginForm reads search params, so it sits under Suspense.
export default function LoginPage() {
  return (
    <div className={styles.screen}>
      <AppHeader title="DocSuri" />
      <h2 className={styles.heading}>로그인</h2>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
