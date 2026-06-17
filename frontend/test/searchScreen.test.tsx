import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchScreen } from '@/components/SearchScreen';

// SearchScreen drives the real MockTransport (mock-first), so these exercise the
// full state machine without a backend.

const push = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

async function submit(query: string) {
  const user = userEvent.setup();
  await user.clear(screen.getByTestId('search-input'));
  if (query) await user.type(screen.getByTestId('search-input'), query);
  await user.click(screen.getByTestId('search-submit'));
}

describe('SearchScreen state machine', () => {
  beforeEach(() => {
    push.mockReset();
    render(<SearchScreen />);
  });

  it('blocks empty submit with an inline error (no request)', async () => {
    await submit('');
    expect(screen.getByTestId('search-inline-error')).toBeInTheDocument();
  });

  it('renders a result list for a normal query', async () => {
    await submit('transformer attention');
    expect(await screen.findByTestId('result-list')).toBeInTheDocument();
    expect(screen.getAllByTestId('result-card').length).toBeGreaterThan(0);
  });

  it('distinguishes empty from abstain', async () => {
    await submit('없음 keyword');
    expect(await screen.findByTestId('state-view-empty')).toBeInTheDocument();

    await submit('기권 keyword');
    expect(await screen.findByTestId('state-view-abstain')).toBeInTheDocument();
  });

  it('shows a degraded banner', async () => {
    await submit('저하 keyword');
    expect(await screen.findByTestId('degraded-banner')).toBeInTheDocument();
  });

  it('surfaces a retry on server error', async () => {
    await submit('오류 keyword');
    expect(await screen.findByTestId('state-view-error')).toBeInTheDocument();
    expect(screen.getByTestId('state-view-retry')).toBeInTheDocument();
  });
});
