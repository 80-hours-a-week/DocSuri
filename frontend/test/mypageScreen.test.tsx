import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MyPageScreen } from '@/components/mypage/MyPageScreen';
import { SessionProvider } from '@/components/session/SessionContext';
import { mockLogin } from '@/mocks/accountFixtures';
import { resetMypageFixtures } from '@/mocks/mypageFixtures';

// Drives the real MockTransport + mypage fixtures (mock-first), so it exercises the
// composite U10 view (profile/ORCID/library/recent/subscription/settings) end-to-end
// without a backend. Subscription assertions mirror backend/tests/test_mypage.py.

vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const push = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

function renderScreen() {
  return render(
    <SessionProvider>
      <MyPageScreen />
    </SessionProvider>,
  );
}

beforeEach(() => {
  mockLogin('mypage-test@example.com');
  resetMypageFixtures();
  push.mockClear();
});

describe('MyPageScreen (U10)', () => {
  it('renders every section, with ORCID shown for the mock ORCID login provider', async () => {
    renderScreen();
    expect(await screen.findByTestId('mypage-profile')).toBeInTheDocument();
    expect(screen.getByTestId('mypage-orcid')).toBeInTheDocument();
    expect(screen.getByTestId('mypage-library')).toBeInTheDocument();
    expect(screen.getByTestId('mypage-recent')).toBeInTheDocument();
    expect(screen.getByTestId('mypage-subscription')).toBeInTheDocument();
    expect(screen.getByTestId('mypage-subscription-status')).toHaveTextContent('구독 없음');
    expect(screen.getByTestId('mypage-settings')).toBeInTheDocument();
  });

  it('subscribes then cancels — benefit retained (status flips to 해지 예약, not gone)', async () => {
    renderScreen();
    await screen.findByTestId('mypage-subscription');
    await userEvent.click(screen.getByTestId('mypage-subscription-subscribe'));
    await waitFor(() =>
      expect(screen.getByTestId('mypage-subscription-status')).toHaveTextContent('구독 중'),
    );
    await userEvent.click(screen.getByTestId('mypage-subscription-cancel'));
    await waitFor(() =>
      expect(screen.getByTestId('mypage-subscription-status')).toHaveTextContent('해지 예약'),
    );
  });

  it('toggles the optional nightly-push consent', async () => {
    renderScreen();
    const checkbox = await screen.findByTestId('mypage-consent-nightly-push');
    expect(checkbox).not.toBeChecked();
    await userEvent.click(checkbox);
    await waitFor(() => expect(checkbox).toBeChecked());
  });

  it('logs out via the shared session and redirects home', async () => {
    renderScreen();
    await screen.findByTestId('mypage-settings');
    await userEvent.click(screen.getByTestId('mypage-logout'));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
  });

  it('withdraws after confirmation and redirects home', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderScreen();
    await screen.findByTestId('mypage-settings');
    await userEvent.click(screen.getByTestId('mypage-withdraw'));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
  });

  it('does not withdraw when the confirmation is dismissed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderScreen();
    await screen.findByTestId('mypage-settings');
    await userEvent.click(screen.getByTestId('mypage-withdraw'));
    expect(push).not.toHaveBeenCalled();
  });
});
