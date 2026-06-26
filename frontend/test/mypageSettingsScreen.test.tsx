import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MyPageSettingsScreen } from '@/components/mypage/MyPageSettingsScreen';
import { SessionProvider } from '@/components/session/SessionContext';
import { mockLogin } from '@/mocks/accountFixtures';
import { resetMypageFixtures } from '@/mocks/mypageFixtures';
import { ApiClient } from '@/lib/api/apiClient';

const push = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

function renderScreen() {
  return render(
    <SessionProvider>
      <MyPageSettingsScreen />
    </SessionProvider>,
  );
}

beforeEach(() => {
  mockLogin('mypage-settings-test@example.com');
  resetMypageFixtures();
  push.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('MyPageSettingsScreen (U10)', () => {
  it('shows mandatory consents read-only and toggles the optional nightly-push consent', async () => {
    renderScreen();
    const checkbox = await screen.findByTestId('mypage-consent-nightly-push');
    expect(checkbox).not.toBeChecked();
    await userEvent.click(checkbox);
    await waitFor(() => expect(checkbox).toBeChecked());
  });

  it('deletes personalization logs and resets the profile from settings', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderScreen();

    await screen.findByTestId('mypage-personalization-data');
    await userEvent.click(screen.getByTestId('mypage-personalization-delete-events'));
    await waitFor(() =>
      expect(screen.getByTestId('mypage-action-notice')).toHaveTextContent(
        '개인맞춤 행동 로그 0건을 삭제했습니다.',
      ),
    );

    await userEvent.click(screen.getByTestId('mypage-personalization-reset-profile'));
    await waitFor(() =>
      expect(screen.getByTestId('mypage-action-notice')).toHaveTextContent(
        '개인맞춤 프로필을 초기화했습니다.',
      ),
    );
  });

  it('keeps the settings page open when personalization settings are unavailable', async () => {
    vi.spyOn(ApiClient.prototype, 'getPersonalizationSettings').mockRejectedValueOnce(
      new Error('disabled'),
    );
    renderScreen();

    expect(await screen.findByTestId('mypage-settings-screen')).toBeInTheDocument();
    expect(screen.getByTestId('mypage-personalization-enabled')).toBeDisabled();
    expect(screen.getByTestId('mypage-personalization-unavailable')).toHaveTextContent(
      '맞춤 서비스 설정을 불러오지 못했습니다.',
    );
  });

  it('does not call destructive personalization actions when confirmation is dismissed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const deleteSpy = vi.spyOn(ApiClient.prototype, 'deletePersonalizationEvents');
    renderScreen();

    await screen.findByTestId('mypage-personalization-data');
    await userEvent.click(screen.getByTestId('mypage-personalization-delete-events'));

    expect(window.confirm).toHaveBeenCalled();
    expect(deleteSpy).not.toHaveBeenCalled();
    expect(screen.queryByTestId('mypage-action-notice')).not.toBeInTheDocument();
  });

  it('toggles the personalization setting', async () => {
    renderScreen();
    const checkbox = await screen.findByTestId('mypage-personalization-enabled');
    expect(checkbox).toBeChecked();

    await userEvent.click(checkbox);

    await waitFor(() => expect(checkbox).not.toBeChecked());
  });

  it('logs out via the shared session and redirects home', async () => {
    renderScreen();
    await screen.findByTestId('mypage-account-actions');
    await userEvent.click(screen.getByTestId('mypage-logout'));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
  });

  it('withdraws after password re-auth prompt and redirects home', async () => {
    // 탈퇴는 현재 비밀번호 재인증(prompt)을 요구한다(감사 H7).
    vi.spyOn(window, 'prompt').mockReturnValue('OldPw123!@x');
    renderScreen();
    await screen.findByTestId('mypage-account-actions');
    await userEvent.click(screen.getByTestId('mypage-withdraw'));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
  });

  it('does not withdraw when the re-auth prompt is dismissed', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null);
    renderScreen();
    await screen.findByTestId('mypage-account-actions');
    await userEvent.click(screen.getByTestId('mypage-withdraw'));
    expect(push).not.toHaveBeenCalled();
  });
});
