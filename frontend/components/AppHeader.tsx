'use client';

import Link from 'next/link';
import styles from './AppHeader.module.css';
import { useSession } from './session/SessionContext';

// AppHeader (LC-1) — minimal top bar with brand + sign-out for authed screens.
export function AppHeader({ title }: { title: string }) {
  const { status, signOut } = useSession();
  // Authenticated users treat the brand as the app home (search); anonymous /
  // first-time visitors land on the hero. The nav flow is silent on this, so
  // this is a code-level navigation choice.
  const brandHref = status === 'authenticated' ? '/search' : '/';
  return (
    <header className={styles.header}>
      <Link href={brandHref} className={styles.brand} data-testid="app-header-brand">
        {title}
      </Link>
      {/* 화면 이동(검색/마이페이지)은 하단 탭바(BottomNav)가 담당한다.
          상단은 브랜드 + 로그아웃만 유지한다. */}
      {status === 'authenticated' ? (
        <button
          type="button"
          className={styles.signout}
          onClick={() => void signOut()}
          data-testid="app-header-signout"
        >
          로그아웃
        </button>
      ) : null}
    </header>
  );
}
