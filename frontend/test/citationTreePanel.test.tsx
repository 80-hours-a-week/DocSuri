import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CitationTreePanel } from '@/components/CitationTreePanel';

describe('CitationTreePanel', () => {
  it('loads the citation tree, expands a node, and saves a saveable citation', async () => {
    const user = userEvent.setup();
    render(<CitationTreePanel paperId="2101.00001" />);

    expect(await screen.findByTestId('citation-tree-panel')).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: '각주 트리' })).toBeInTheDocument();
    expect(await screen.findByText('Attention Is All You Need')).toBeInTheDocument();
    expect(screen.getByText(/├──/)).toBeInTheDocument();
    expect(screen.getByText(/OpenReview workshop record/)).toBeInTheDocument();

    await user.click(screen.getByTestId('citation-expand-1706.03762'));
    expect(
      await screen.findByText(
        'Neural Machine Translation by Jointly Learning to Align and Translate',
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByTestId('citation-save-1706.03762'));
    expect(await screen.findByText('저장됨')).toBeInTheDocument();
  });
});
