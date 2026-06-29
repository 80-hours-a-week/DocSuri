import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouteGuard } from '@/components/RouteGuard';
import { SessionProvider, useSession } from '@/components/session/SessionContext';
import { mockLogin } from '@/mocks/accountFixtures';

const replace = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
}));

function LogoutButton() {
  const { signOut } = useSession();
  return (
    <button type="button" onClick={() => void signOut()}>
      로그아웃
    </button>
  );
}

beforeEach(() => {
  mockLogin('route-guard-test@example.com');
  replace.mockClear();
});

describe('RouteGuard', () => {
  it('shows logout-specific loading copy while signing out', async () => {
    render(
      <SessionProvider>
        <RouteGuard redirectTo="/search">
          <LogoutButton />
        </RouteGuard>
      </SessionProvider>,
    );

    await userEvent.click(await screen.findByRole('button', { name: '로그아웃' }));

    expect(await screen.findByText('로그아웃 중…')).toBeInTheDocument();
    expect(screen.queryByText('검색 중…')).not.toBeInTheDocument();
    await waitFor(() => expect(replace).not.toHaveBeenCalled());
  });
});
