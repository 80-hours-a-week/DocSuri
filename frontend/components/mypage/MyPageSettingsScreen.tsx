'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getApiClient } from '@/lib/api';
import { useSession } from '../session/SessionContext';
import { StateView } from '../StateView';
import styles from './MyPageScreen.module.css';
import type { ConsentSettingsVM } from '@/types/mypage';

// MyPageSettingsScreen (U10) — 동의 철회(야간 푸시만 선택 동의라 토글 가능, 개인정보처리방침/
// 이용약관은 가입 시 필수 동의라 철회 불가·읽기 전용) + 로그아웃 + 회원탈퇴.

type BusyKey = 'consent' | 'logout' | 'withdraw' | null;

export function MyPageSettingsScreen() {
  const { signOut } = useSession();
  const router = useRouter();
  const [consents, setConsents] = useState<ConsentSettingsVM | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [busy, setBusy] = useState<BusyKey>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus('loading');
    try {
      const result = await getApiClient().getConsents();
      setConsents(result);
      setStatus('ready');
    } catch {
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const withBusy = async (key: NonNullable<BusyKey>, action: () => Promise<void>) => {
    setBusy(key);
    setActionError(null);
    try {
      await action();
    } catch {
      setActionError('처리하지 못했습니다. 다시 시도해 주세요.');
    } finally {
      setBusy(null);
    }
  };

  const onToggleNightlyPush = (checked: boolean) =>
    withBusy('consent', async () => {
      const result = await getApiClient().updateNightlyPushConsent(checked);
      setConsents(result);
    });

  const onLogout = () =>
    withBusy('logout', async () => {
      await signOut();
      router.push('/');
    });

  const onWithdraw = () =>
    withBusy('withdraw', async () => {
      if (!window.confirm('회원탈퇴 시 계정이 비활성화됩니다. 계속하시겠습니까?')) return;
      await getApiClient().withdrawAccount();
      await signOut();
      router.push('/');
    });

  if (status === 'loading') return <StateView kind="loading" title="설정을 불러오는 중…" />;
  if (status === 'error' || !consents) return <StateView kind="error" onRetry={() => void load()} />;

  return (
    <section className={styles.screen} data-testid="mypage-settings-screen">
      {actionError ? (
        <p className={styles.error} role="alert" data-testid="mypage-action-error">
          {actionError}
        </p>
      ) : null}

      <section className={styles.card} data-testid="mypage-consents">
        <h2 className={styles.cardTitle}>동의 철회</h2>
        <label className={styles.toggleRow}>
          <span>개인정보처리방침 동의 (가입 시 필수, 철회 불가)</span>
          <input type="checkbox" checked={consents.privacyPolicyAgreed} disabled readOnly />
        </label>
        <label className={styles.toggleRow}>
          <span>서비스 이용약관 동의 (가입 시 필수, 철회 불가)</span>
          <input type="checkbox" checked={consents.termsOfServiceAgreed} disabled readOnly />
        </label>
        <label className={styles.toggleRow}>
          <span>야간 푸시 알림 동의 (이메일 · 최신/관심 논문 등재 알림)</span>
          <input
            type="checkbox"
            checked={consents.nightlyPushAgreed}
            disabled={busy === 'consent'}
            onChange={(e) => void onToggleNightlyPush(e.target.checked)}
            data-testid="mypage-consent-nightly-push"
          />
        </label>
      </section>

      <section className={styles.card} data-testid="mypage-account-actions">
        <h2 className={styles.cardTitle}>계정</h2>
        <button
          type="button"
          className={styles.action}
          disabled={busy === 'logout'}
          onClick={() => void onLogout()}
          data-testid="mypage-logout"
        >
          로그아웃
        </button>
        <button
          type="button"
          className={styles.danger}
          disabled={busy === 'withdraw'}
          onClick={() => void onWithdraw()}
          data-testid="mypage-withdraw"
        >
          회원탈퇴
        </button>
      </section>
    </section>
  );
}
