import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StateView } from '@/components/StateView';

describe('StateView', () => {
  it('shows distinct messages for abstain vs empty (BR-U5-9)', () => {
    const { unmount } = render(<StateView kind="empty" />);
    expect(screen.getByTestId('state-view-empty')).toHaveTextContent('검색 결과가 없습니다');
    unmount();

    render(<StateView kind="abstain" />);
    const abstain = screen.getByTestId('state-view-abstain');
    expect(abstain).toHaveTextContent('확실한 근거를 찾지 못했습니다');
    expect(abstain).not.toHaveTextContent('검색 결과가 없습니다');
  });

  it('offers a retry only on error', () => {
    const { unmount } = render(<StateView kind="error" onRetry={() => {}} />);
    expect(screen.getByTestId('state-view-retry')).toBeInTheDocument();
    unmount();
    render(<StateView kind="empty" onRetry={() => {}} />);
    expect(screen.queryByTestId('state-view-retry')).toBeNull();
  });
});
