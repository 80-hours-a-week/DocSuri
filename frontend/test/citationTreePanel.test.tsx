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
    expect(screen.getByTestId('citation-graph')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '확대' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '축소' })).toBeInTheDocument();
    expect(screen.getByText(/OpenReview workshop record/)).toBeInTheDocument();

    const zoomOut = screen.getByRole('button', { name: '축소' });
    await user.click(zoomOut);
    await user.click(zoomOut);
    await user.click(zoomOut);
    expect(screen.getByText('25%')).toBeInTheDocument();
    expect(zoomOut).toBeDisabled();

    const parentExpand = screen.getByTestId('citation-expand-1706.03762');
    await user.click(parentExpand);
    expect(
      await screen.findByText(
        'Neural Machine Translation by Jointly Learning to Align and Translate',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('citation-expand-1409.0473')).not.toBeInTheDocument();
    expect(parentExpand).toHaveTextContent('축소');

    await user.click(parentExpand);
    expect(
      screen.queryByText('Neural Machine Translation by Jointly Learning to Align and Translate'),
    ).not.toBeInTheDocument();
    expect(parentExpand).toHaveTextContent('확장');

    await user.click(screen.getByTestId('citation-save-1706.03762'));
    expect(await screen.findByText('저장됨')).toBeInTheDocument();
  });
});
