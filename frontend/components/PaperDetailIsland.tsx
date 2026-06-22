'use client';

// PaperDetailIsland (P3·P5) — the client island inside the SSR /paper/[id] shell.
// Owns everything under the DocSuri header: a sticky 요약/초록번역/전문번역 action bar
// (each opens SummaryModal at the matching tab), the paper metadata (title/authors/
// abstract), and the normalized S3 full-text body. Choosing a summary anchor closes
// the modal and highlights the span in the on-page body (Q5=C). real-first: real BFF
// transport, mock in dev (NEXT_PUBLIC_… unset).
import { useState } from 'react';
import type { AnchorVM } from '@/types/generated';
import { usePaperMeta } from '@/lib/usePaperMeta';
import { FullTextViewer } from './FullTextViewer';
import { SummaryModal, type DetailView } from './SummaryModal';
import { SaveToLibraryButton } from './SaveToLibraryButton';
import styles from './PaperDetailIsland.module.css';

interface PaperDetailIslandProps {
  paperId: string;
  version: number;
  arxivUrl?: string;
}

const ACTIONS: { view: DetailView; label: string }[] = [
  { view: 'summary', label: '요약' },
  { view: 'abstractTrans', label: '초록 번역' },
  { view: 'fullTrans', label: '전문 번역' },
];

export function PaperDetailIsland({ paperId, version, arxivUrl }: PaperDetailIslandProps) {
  const [anchor, setAnchor] = useState<AnchorVM | null>(null);
  const [modalView, setModalView] = useState<DetailView | null>(null);
  const meta = usePaperMeta(paperId);

  return (
    <div className={styles.root}>
      {/* Sticky action bar directly under the DocSuri header — each button opens the
          summary/translation modal at its tab. */}
      <div className={styles.actionsBar} role="group" aria-label="요약/번역 액션">
        {ACTIONS.map((a) => (
          <button
            key={a.view}
            type="button"
            className={styles.action}
            onClick={() => setModalView(a.view)}
            data-testid={`open-${a.view}`}
          >
            {a.label}
          </button>
        ))}
      </div>

      {meta.status === 'done' && meta.meta ? (
        <header className={styles.meta} data-testid="paper-meta">
          <div className={styles.titleRow}>
            <h1 className={styles.title} data-testid="paper-title">
              {meta.meta.title}
            </h1>
            <SaveToLibraryButton
              card={{
                arxivId: paperId,
                title: meta.meta.title,
                authors: meta.meta.authors,
                year: meta.meta.year,
                abstractSnippet: meta.meta.abstract,
                arxivUrl: meta.meta.arxivUrl ?? arxivUrl,
              }}
            />
          </div>
          <p className={styles.authors} data-testid="paper-authors">
            {meta.meta.authors.join(', ')}
            {meta.meta.year ? <span className={styles.year}> · {meta.meta.year}</span> : null}
          </p>
          <p className={styles.abstract} data-testid="paper-abstract">
            {meta.meta.abstract}
          </p>
          <p className={styles.idline}>
            <span>arXiv:{paperId}</span>
            {arxivUrl ? (
              <a className={styles.link} href={arxivUrl} target="_blank" rel="noopener noreferrer">
                arXiv에서 원문 보기
              </a>
            ) : null}
          </p>
        </header>
      ) : meta.status === 'loading' ? (
        <p className={styles.metaLoading} data-testid="paper-meta-loading">
          논문 정보를 불러오는 중…
        </p>
      ) : null}

      {/* Body-first: the normalized S3 full text, with anchor highlight when set. */}
      <section className={styles.bodySection} aria-label="원문 전문">
        <h2 className={styles.bodyHeading}>원문 전문</h2>
        <FullTextViewer paperId={paperId} version={version} anchor={anchor} arxivUrl={arxivUrl} />
      </section>

      {modalView ? (
        <SummaryModal
          paperId={paperId}
          version={version}
          view={modalView}
          onClose={() => setModalView(null)}
          onAnchor={setAnchor}
        />
      ) : null}
    </div>
  );
}
