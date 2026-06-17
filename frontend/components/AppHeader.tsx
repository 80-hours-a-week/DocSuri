'use client';

import Link from 'next/link';
import styles from './AppHeader.module.css';
import { useSession } from './session/SessionContext';

// AppHeader (LC-1) — minimal top bar with brand + sign-out for authed screens.
export function AppHeader({ title }: { title: string }) {
  const { status, signOut } = useSession();
  return (
    <header className={styles.header}>
      <Link href="/" className={styles.brand} data-testid="app-header-brand">
        {title}
      </Link>
      {status === 'authenticated' ? (
        <nav className={styles.nav} aria-label="주요 메뉴">
          <Link href="/search" className={styles.navLink} data-testid="app-header-search">
            검색
          </Link>
          <Link href="/library" className={styles.navLink} data-testid="app-header-library">
            라이브러리
          </Link>
          <button
            type="button"
            className={styles.signout}
            onClick={() => void signOut()}
            data-testid="app-header-signout"
          >
            로그아웃
          </button>
        </nav>
      ) : null}
    </header>
  );
}
