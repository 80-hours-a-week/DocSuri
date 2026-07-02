import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TranslationView } from '@/components/TranslationView';
import { resetMockGlossary } from '@/mocks/summarizeFixtures';
import type { TranslationVM } from '@/types/generated';

// 개인 용어집 (BR-S4) — drives the real MockTransport end to end through TranslationView, which
// shows 원어 유지 용어 (other kept terms → weak) first, then 표준 용어 (seed standard: keep-as-is +
// mapping chips, both → strong; mappings pre-filled). Only one editor opens; outside click dismisses.

const translation: TranslationVM = {
  docModel: {
    meta: {
      paperId: '2401.1',
      version: 1,
      title: '',
      provenance: {
        sourceTier: 'ar5iv',
        parserVersion: 'test',
        schemaVersion: '1.0.0',
        generatedAt: '2026-06-23T00:00:00Z',
      },
    },
    fullText: '어텐션만으로 시퀀스를 변환한다.',
    sections: [
      {
        id: 's1',
        title: '',
        blocks: [{ id: 's1.p1', type: 'paragraph', text: '어텐션만으로 시퀀스를 변환한다.' }],
      },
    ],
  },
  keptTerms: ['Transformer', 'encoder', 'BLEU'],
  standardGlossary: [
    { term: 'Transformer' }, // keep-as-is standard → strong badge
    { term: 'BLEU' }, // keep-as-is standard → strong badge
    { term: 'attention', translated: '어텐션' }, // mapping → editable strong (pre-filled 어텐션)
  ],
};

// Badges are selected by term (order-independent): encoder (원어 유지 → weak), Transformer / BLEU
// (표준 → strong).
const badge = (term: string) => screen.getByRole('button', { name: term });

function renderView() {
  return render(
    <div>
      <TranslationView translation={translation} showGlossary />
      <button type="button" data-testid="outside">
        바깥
      </button>
    </div>,
  );
}

describe('GlossaryTermBadge (via TranslationView)', () => {
  beforeEach(() => {
    resetMockGlossary();
  });

  it('renders both groups; the mapping is an editable 표준 badge', () => {
    renderView();
    expect(screen.getByRole('heading', { name: '원어 유지 용어' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '표준 용어' })).toBeInTheDocument();
    // encoder (원어 유지) + Transformer, BLEU, attention (표준) — attention is editable now too.
    expect(screen.getAllByTestId('glossary-badge')).toHaveLength(4);
    expect(badge('attention')).toBeInTheDocument();
    expect(badge('encoder')).not.toHaveAttribute('data-saved'); // unedited → no marker
  });

  it('hides the 표준 용어 group when the paper has no standard terms', () => {
    render(<TranslationView translation={{ ...translation, standardGlossary: [] }} showGlossary />);
    // No standard terms → the 표준 용어 section (heading + chips) is not rendered at all.
    expect(screen.queryByRole('heading', { name: '표준 용어' })).not.toBeInTheDocument();
    // 원어 유지 용어 still shows (every kept term is now non-standard).
    expect(screen.getByRole('heading', { name: '원어 유지 용어' })).toBeInTheDocument();
    expect(screen.getAllByTestId('glossary-badge')).toHaveLength(3);
  });

  it('a mapping (attention) pre-fills the standard rendering and saves as strong', async () => {
    const user = userEvent.setup();
    renderView();

    await user.click(badge('attention'));
    const input = (await screen.findByTestId('glossary-input')) as HTMLInputElement;
    expect(input.value).toBe('어텐션'); // standard rendering pre-filled (defaultValue)

    await user.clear(input);
    await user.type(input, '주목');
    await user.click(screen.getByTestId('glossary-save'));
    await waitFor(() => expect(screen.getByTestId('glossary-saved')).toBeInTheDocument());
    expect(screen.getByTestId('glossary-saved')).toHaveTextContent('번역을 다시 만드는 중'); // strong
  });

  it('opens an editor on tap and confirms a weak save', async () => {
    const user = userEvent.setup();
    renderView();
    expect(screen.queryByTestId('glossary-input')).not.toBeInTheDocument();

    await user.click(badge('encoder')); // 원어 유지 → weak
    const input = await screen.findByTestId('glossary-input');
    expect(screen.getByTestId('glossary-save')).toBeDisabled();

    await user.type(input, '인코더');
    expect(screen.getByTestId('glossary-save')).toBeEnabled();

    await user.click(screen.getByTestId('glossary-save'));
    await waitFor(() => expect(screen.getByTestId('glossary-saved')).toBeInTheDocument());
    expect(screen.getByTestId('glossary-saved')).toHaveTextContent('바로 반영');
    // Personalized → the chip is now marked (amber), showing only the term (no inline rendering).
    expect(badge('encoder')).toHaveAttribute('data-saved', 'true');
    expect(badge('encoder')).toHaveTextContent('encoder');
  });

  it('keeps only one editor open at a time', async () => {
    const user = userEvent.setup();
    renderView();

    await user.click(badge('encoder'));
    expect(await screen.findByTestId('glossary-input')).toBeInTheDocument();
    expect(screen.getAllByTestId('glossary-input')).toHaveLength(1);

    await user.click(badge('Transformer'));
    await waitFor(() => expect(screen.getAllByTestId('glossary-input')).toHaveLength(1));
  });

  it('closes the editor on an outside click', async () => {
    const user = userEvent.setup();
    renderView();

    await user.click(badge('encoder'));
    expect(await screen.findByTestId('glossary-input')).toBeInTheDocument();

    await user.click(screen.getByTestId('outside'));
    await waitFor(() => expect(screen.queryByTestId('glossary-input')).not.toBeInTheDocument());
  });

  it('a 표준 용어 saves as strong (re-translation)', async () => {
    const user = userEvent.setup();
    renderView();

    // 'Transformer' is a 표준 용어 (keep-as-is) → saving it is a strong, re-translated override.
    await user.click(badge('Transformer'));
    await user.type(await screen.findByTestId('glossary-input'), '트랜스포머');
    await user.click(screen.getByTestId('glossary-save'));
    await waitFor(() => expect(screen.getByTestId('glossary-saved')).toBeInTheDocument());
    expect(screen.getByTestId('glossary-saved')).toHaveTextContent('번역을 다시 만드는 중');

    await user.click(screen.getByTestId('outside'));
    expect(badge('Transformer')).toHaveAttribute('data-saved', 'true');
  });

  it('pre-fills a previously saved rendering when reopened', async () => {
    const user = userEvent.setup();
    renderView();

    await user.click(badge('encoder'));
    await user.type(await screen.findByTestId('glossary-input'), '인코더');
    await user.click(screen.getByTestId('glossary-save'));
    await waitFor(() => expect(screen.getByTestId('glossary-saved')).toBeInTheDocument());

    await user.click(screen.getByTestId('outside'));
    await user.click(badge('encoder'));
    const reopened = (await screen.findByTestId('glossary-input')) as HTMLInputElement;
    expect(reopened.value).toBe('인코더');
  });
});
