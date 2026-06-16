'use client';

import Link from 'next/link';
import styles from './HeroLanding.module.css';
import { useSession } from './session/SessionContext';

// HeroLanding (LC-1, US-H1) — the magic-moment entry. Authenticated users go
// straight to search; anonymous users are nudged to sign up / log in (search
// requires auth, U2 FD §Q5=A).

export function HeroLanding() {
  const { status } = useSession();

  return (
    <section className={styles.root} data-testid="hero-landing">
      <h1 className={styles.title}>DocSuri</h1>
      <p className={styles.subtitle}>
        질문을 입력하면 근거 있는 논문을 찾아드려요.
      </p>

      {status === 'authenticated' ? (
        <Link href="/search" className={styles.primary} data-testid="hero-cta-search">
          검색 시작하기
        </Link>
      ) : (
        <div className={styles.actions}>
          <Link href="/signup" className={styles.primary} data-testid="hero-cta-signup">
            시작하기
          </Link>
          <Link href="/login?redirect=/search" className={styles.secondary} data-testid="hero-cta-login">
            로그인
          </Link>
        </div>
      )}
    </section>
  );
}
