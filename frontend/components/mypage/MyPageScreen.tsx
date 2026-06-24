'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getApiClient } from '@/lib/api';
import { useSession } from '../session/SessionContext';
import { StateView } from '../StateView';
import { cardFromMeta } from '@/lib/library/cardFromMeta';
import styles from './MyPageScreen.module.css';
import type { LibraryItemDTO, SubscriptionDTO } from '@/types/generated';
import type {
  AccountProfileVM,
  ConsentSettingsVM,
  OrcidProfileVM,
  RecentlyViewedItemVM,
} from '@/types/mypage';

// MyPageScreen (U10) — composite view over U3(profile)/U4(library)/U9(recently viewed) +
// U10's own subscription (REAL) and ORCID/profile/consent/withdrawal (MOCK until U3 ships
// the real endpoints, see lib/api/apiClient.ts mypage section). 관심 논문은 U4
// listLibrary()를 그대로 호출(capped to 3, "라이브러리 전체보기"로 연결) — 별도 저장소 없음.

const LOGIN_PROVIDER_LABEL: Record<string, string> = {
  GOOGLE: 'Google',
  ORCID: 'ORCID',
};

const SUBSCRIPTION_LABEL: Record<string, string> = {
  NONE: '구독 없음',
  ACTIVE: '구독 중 (PREMIUM)',
  CANCELED: '해지 예약',
};

interface LoadedState {
  profile: AccountProfileVM;
  orcid: OrcidProfileVM | null;
  library: LibraryItemDTO[];
  recentlyViewed: RecentlyViewedItemVM[];
  subscription: SubscriptionDTO;
  consents: ConsentSettingsVM;
}

type BusyKey = 'subscribe' | 'cancel' | 'consent' | 'logout' | 'withdraw' | null;

export function MyPageScreen() {
  const { signOut } = useSession();
  const router = useRouter();
  const [data, setData] = useState<LoadedState | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [busy, setBusy] = useState<BusyKey>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus('loading');
    try {
      const client = getApiClient();
      const [profile, library, recentlyViewed, subscription, consents] = await Promise.all([
        client.getAccountProfile(),
        client.listLibrary({ limit: 3 }),
        client.getRecentlyViewed(),
        client.getSubscription(),
        client.getConsents(),
      ]);
      const orcid = profile.loginProvider === 'ORCID' ? await client.getOrcidProfile() : null;
      setData({ profile, orcid, library: library.items, recentlyViewed, subscription, consents });
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

  const onSubscribe = () =>
    withBusy('subscribe', async () => {
      const subscription = await getApiClient().subscribe();
      setData((prev) => (prev ? { ...prev, subscription } : prev));
    });

  const onCancelSubscription = () =>
    withBusy('cancel', async () => {
      const subscription = await getApiClient().cancelSubscription();
      setData((prev) => (prev ? { ...prev, subscription } : prev));
    });

  const onToggleNightlyPush = (checked: boolean) =>
    withBusy('consent', async () => {
      const consents = await getApiClient().updateNightlyPushConsent(checked);
      setData((prev) => (prev ? { ...prev, consents } : prev));
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

  if (status === 'loading') return <StateView kind="loading" title="마이페이지를 불러오는 중…" />;
  if (status === 'error' || !data) return <StateView kind="error" onRetry={() => void load()} />;

  const { profile, orcid, library, recentlyViewed, subscription, consents } = data;

  return (
    <section className={styles.screen} data-testid="mypage-screen">
      {actionError ? (
        <p className={styles.error} role="alert" data-testid="mypage-action-error">
          {actionError}
        </p>
      ) : null}

      <section className={styles.card} data-testid="mypage-profile">
        <h2 className={styles.cardTitle}>계정</h2>
        <p>
          로그인 경로:{' '}
          <strong>{LOGIN_PROVIDER_LABEL[profile.loginProvider] ?? profile.loginProvider}</strong>
        </p>
        <p className={styles.muted}>가입일: {new Date(profile.createdAt).toLocaleDateString('ko-KR')}</p>
      </section>

      {orcid ? (
        <section className={styles.card} data-testid="mypage-orcid">
          <h2 className={styles.cardTitle}>ORCID</h2>
          <p>
            {orcid.name}
            {orcid.affiliation ? ` · ${orcid.affiliation}` : ''}
          </p>
          <p className={styles.muted}>{orcid.orcidId}</p>
          {orcid.works.length > 0 ? (
            <ul className={styles.plainList}>
              {orcid.works.map((work) => (
                <li key={work.title}>
                  {work.title}
                  {work.year ? ` (${work.year})` : ''}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      <section className={styles.card} data-testid="mypage-library">
        <h2 className={styles.cardTitle}>관심 논문</h2>
        {library.length === 0 ? (
          <p className={styles.muted}>아직 저장한 논문이 없습니다.</p>
        ) : (
          <ul className={styles.plainList}>
            {library.map((item) => {
              const card = cardFromMeta(item.meta);
              return (
                <li key={String(item.id)} data-testid="mypage-library-item">
                  <Link href={`/paper/${encodeURIComponent(card.arxivId)}`}>{card.title}</Link>
                </li>
              );
            })}
          </ul>
        )}
        <Link href="/library" className={styles.more} data-testid="mypage-library-more">
          라이브러리 전체보기
        </Link>
      </section>

      <section className={styles.card} data-testid="mypage-recent">
        <h2 className={styles.cardTitle}>최근 본 논문</h2>
        {recentlyViewed.length === 0 ? (
          <p className={styles.muted}>최근 본 논문이 없습니다.</p>
        ) : (
          <ul className={styles.plainList}>
            {recentlyViewed.map((item) => (
              <li key={item.arxivId} data-testid="mypage-recent-item">
                <Link href={`/paper/${encodeURIComponent(item.arxivId)}`}>{item.title}</Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.card} data-testid="mypage-subscription">
        <h2 className={styles.cardTitle}>내 구독</h2>
        <p>
          상태:{' '}
          <strong data-testid="mypage-subscription-status">
            {SUBSCRIPTION_LABEL[subscription.status] ?? subscription.status}
          </strong>
        </p>
        {subscription.currentPeriodEnd ? (
          <p className={styles.muted}>
            {subscription.status === 'CANCELED' ? '혜택 유지 기한' : '다음 결제일'}:{' '}
            {new Date(subscription.currentPeriodEnd).toLocaleDateString('ko-KR')}
          </p>
        ) : null}
        {subscription.status === 'ACTIVE' ? (
          <button
            type="button"
            className={styles.action}
            disabled={busy === 'cancel'}
            onClick={() => void onCancelSubscription()}
            data-testid="mypage-subscription-cancel"
          >
            구독 해지
          </button>
        ) : (
          <button
            type="button"
            className={styles.action}
            disabled={busy === 'subscribe'}
            onClick={() => void onSubscribe()}
            data-testid="mypage-subscription-subscribe"
          >
            프리미엄 구독하기
          </button>
        )}
      </section>

      <section className={styles.card} data-testid="mypage-settings">
        <h2 className={styles.cardTitle}>설정</h2>
        <label className={styles.toggleRow}>
          <span>야간 푸시 알림 (이메일 · 최신/관심 논문 등재 알림)</span>
          <input
            type="checkbox"
            checked={consents.nightlyPushAgreed}
            disabled={busy === 'consent'}
            onChange={(e) => void onToggleNightlyPush(e.target.checked)}
            data-testid="mypage-consent-nightly-push"
          />
        </label>
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
