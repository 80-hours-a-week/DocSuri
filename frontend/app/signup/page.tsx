import styles from '../page.module.css';
import { AppHeader } from '@/components/AppHeader';
import { SignupForm } from '@/components/SignupForm';

// Signup route (US-A1).
export default function SignupPage() {
  return (
    <div className={styles.screen}>
      <AppHeader title="DocSuri" />
      <h2 className={styles.heading}>가입하기</h2>
      <SignupForm />
    </div>
  );
}
