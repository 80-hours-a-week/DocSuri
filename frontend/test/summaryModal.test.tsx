import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SummaryModal } from '@/components/SummaryModal';

// Drives the real MockTransport (mock-first) end to end. Regression guard: the
// summary must render once and STAY rendered — a request loop (run re-firing on
// every status change) would flip the modal back to the loading state forever.

describe('SummaryModal', () => {
  it('renders mock summary data and does not loop back to loading', async () => {
    render(
      <SummaryModal paperId="1706.03762v5" version={1} view="summary" onClose={() => {}} onAnchor={() => {}} />,
    );

    // Mock fixture content appears (not stuck on "요약 생성 중…").
    expect(await screen.findByTestId('summary-view')).toBeInTheDocument();
    expect(screen.getByText(/Transformer/)).toBeInTheDocument();

    // After the mock latency window, it must still show the summary (no re-loop).
    await new Promise((r) => setTimeout(r, 400));
    expect(screen.getByTestId('summary-view')).toBeInTheDocument();
    expect(screen.queryByTestId('state-view-loading')).not.toBeInTheDocument();
  });

  it('shows the persona toggle for summary and renders a translation view for 번역', async () => {
    const { rerender } = render(
      <SummaryModal paperId="1706.03762v5" version={1} view="summary" onClose={() => {}} onAnchor={() => {}} />,
    );
    expect(screen.getByTestId('persona-expert')).toBeInTheDocument();

    rerender(
      <SummaryModal
        paperId="1706.03762v5"
        version={1}
        view="abstractTrans"
        onClose={() => {}}
        onAnchor={() => {}}
      />,
    );
    // No persona toggle on translation; the Korean translation text renders.
    expect(screen.queryByTestId('persona-expert')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Transformer를 제안한다/)).toBeInTheDocument());
  });
});
