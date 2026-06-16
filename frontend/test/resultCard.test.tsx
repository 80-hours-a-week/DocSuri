import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResultCard } from '@/components/ResultCard';
import type { ResultCardVM } from '@/types/generated';

const base: ResultCardVM = {
  title: 'Attention Is All You Need',
  authors: ['A. Vaswani', 'N. Shazeer'],
  year: 2017,
  arxivId: '1706.03762v5',
  abstractSnippet: 'The dominant sequence transduction models…',
  relevance: '높음',
  arxivUrl: 'https://arxiv.org/abs/1706.03762',
};

describe('ResultCard', () => {
  it('renders the 7 exposed fields', () => {
    render(<ResultCard card={base} />);
    expect(screen.getByTestId('result-card-title')).toHaveTextContent('Attention Is All You Need');
    expect(screen.getByTestId('result-card-authors')).toHaveTextContent('A. Vaswani, N. Shazeer');
    expect(screen.getByTestId('result-card-year')).toHaveTextContent('2017');
    expect(screen.getByTestId('result-card-arxiv-id')).toHaveTextContent('1706.03762v5');
    expect(screen.getByTestId('result-card-relevance')).toHaveTextContent('높음');
    const link = screen.getByTestId('result-card-link');
    expect(link).toHaveAttribute('href', 'https://arxiv.org/abs/1706.03762');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('drops a non-http(s) link (BR-U5-7)', () => {
    render(<ResultCard card={{ ...base, arxivUrl: 'javascript:alert(1)' }} />);
    expect(screen.queryByTestId('result-card-link')).toBeNull();
  });

  it('renders external text as escaped content (no raw HTML injection)', () => {
    render(<ResultCard card={{ ...base, title: '<img src=x onerror=alert(1)>' }} />);
    const title = screen.getByTestId('result-card-title');
    expect(title).toHaveTextContent('<img src=x onerror=alert(1)>');
    expect(title.querySelector('img')).toBeNull();
  });
});
