'use client';

// DocModelViewer (자체 리치뷰, D4/Q5=C, BR-SF-11) — renders the structured doc-model:
// nested sections + TOC, KaTeX formulas, structured tables (DATA, not crops — D8), and
// webp figures joined to the /assets signed urls by assetId (SEC-9 — the doc-model is
// url-free). OA-license-gated: license_unavailable → arXiv link-out. External text is
// escaped by React (BR-SF-9). Replaces the plain-text FullTextViewer.
//
// NOTE: anchor highlight matches the summary anchor's label ("Table 1"/"Figure 2") to a
// block's anchorLabel (the AnchorVM still carries a label, not a doc-model id — the
// id-based anchor contract is a follow-up). Span-precise inline highlight is a follow-up.
import 'katex/dist/katex.min.css';
import { useEffect, useMemo, useRef } from 'react';
import type { AnchorVM, AssetRef, DocBlock, DocModel, DocSection } from '@/types/generated';
import { useDocModel } from '@/lib/useDocModel';
import { useAssets } from '@/lib/useAssets';
import { MathDisplay, renderInlineMath } from '@/lib/renderMath';
import { StateView } from './StateView';
import styles from './DocModelViewer.module.css';

interface DocModelViewerProps {
  paperId: string;
  version: number;
  /** Summary source anchor to scroll to / highlight, if any (matched by label). */
  anchor?: AnchorVM | null;
  arxivUrl?: string;
}

export function DocModelViewer({ paperId, version, anchor, arxivUrl }: DocModelViewerProps) {
  const { state, load } = useDocModel();
  const { state: assetState, load: loadAssets } = useAssets();
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void load({ paperId, version });
    void loadAssets(paperId, version); // figures join these signed urls by assetId
  }, [paperId, version, load, loadAssets]);

  const assetsById = useMemo(() => {
    const map = new Map<string, AssetRef>();
    if (assetState.status === 'done' && assetState.outcome.kind === 'assets') {
      for (const a of assetState.outcome.assets) map.set(a.assetId, a);
    }
    return map;
  }, [assetState]);

  const docModel =
    state.status === 'done' && state.outcome.kind === 'page' ? state.outcome.docModel : null;

  // Scroll to + highlight the block whose anchorLabel matches the selected anchor.
  useEffect(() => {
    if (!docModel || !anchor || !containerRef.current) return;
    const id = findBlockIdByLabel(docModel, anchor.label);
    if (!id) return;
    const el = containerRef.current.querySelector<HTMLElement>(`[data-block="${cssEscape(id)}"]`);
    if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [docModel, anchor]);

  if (state.status === 'idle' || state.status === 'loading') {
    return <StateView kind="loading" title="본문 불러오는 중…" message="본문을 가져오고 있어요." />;
  }

  const { outcome } = state;
  const safeArxivUrl =
    arxivUrl && (arxivUrl.startsWith('http://') || arxivUrl.startsWith('https://'))
      ? arxivUrl
      : undefined;

  switch (outcome.kind) {
    case 'licenseUnavailable':
      return (
        <div className={styles.gate} data-testid="docmodel-license">
          <StateView kind="licenseUnavailable" />
          {safeArxivUrl ? (
            <a className={styles.link} href={safeArxivUrl} target="_blank" rel="noopener noreferrer">
              arXiv에서 원문 보기
            </a>
          ) : null}
        </div>
      );
    case 'sourceUnavailable':
      return <StateView kind="sourceUnavailable" />;
    case 'error':
      return (
        <StateView kind="error" message={outcome.message} onRetry={() => load({ paperId, version })} />
      );
    case 'page':
      return (
        <div className={styles.root} data-testid="docmodel-viewer" ref={containerRef}>
          <DocTOC sections={outcome.docModel.sections} />
          <article className={styles.body}>
            {outcome.docModel.sections.map((s) => (
              <SectionView key={s.id} section={s} depth={1} assetsById={assetsById} anchor={anchor} />
            ))}
          </article>
        </div>
      );
  }
}

// ---- table of contents (anchor jump) ------------------------------------

function DocTOC({ sections }: { sections: DocSection[] }) {
  const entries = useMemo(() => flattenToc(sections), [sections]);
  if (entries.length === 0) return null;
  return (
    <nav className={styles.toc} aria-label="목차" data-testid="docmodel-toc">
      <p className={styles.tocTitle}>목차</p>
      <ul>
        {entries.map((e) => (
          <li key={e.id} style={{ paddingInlineStart: `${(e.depth - 1) * 12}px` }}>
            <a
              href={`#dm-${e.id}`}
              onClick={(ev) => {
                ev.preventDefault();
                document
                  .getElementById(`dm-${e.id}`)
                  ?.scrollIntoView({ block: 'start', behavior: 'smooth' });
              }}
            >
              {e.title || '(무제 섹션)'}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// ---- section + block rendering ------------------------------------------

function SectionView({
  section,
  depth,
  assetsById,
  anchor,
}: {
  section: DocSection;
  depth: number;
  assetsById: Map<string, AssetRef>;
  anchor?: AnchorVM | null;
}) {
  const Heading = `h${Math.min(depth + 1, 6)}` as keyof React.JSX.IntrinsicElements;
  return (
    <section id={`dm-${section.id}`} className={styles.section}>
      {section.title ? <Heading className={styles.heading}>{section.title}</Heading> : null}
      {section.blocks.map((b) => (
        <BlockView key={b.id} block={b} assetsById={assetsById} active={isActive(b, anchor)} />
      ))}
      {(section.sections ?? []).map((s) => (
        <SectionView key={s.id} section={s} depth={depth + 1} assetsById={assetsById} anchor={anchor} />
      ))}
    </section>
  );
}

function BlockView({
  block,
  assetsById,
  active,
}: {
  block: DocBlock;
  assetsById: Map<string, AssetRef>;
  active: boolean;
}) {
  const cls = active ? `${styles.block} ${styles.active}` : styles.block;
  switch (block.type) {
    case 'paragraph':
      return (
        <p className={cls} data-block={block.id}>
          {renderInlineMath(block.text)}
        </p>
      );
    case 'formula':
      return (
        <div className={`${cls} ${styles.formula}`} data-block={block.id}>
          <MathDisplay latex={block.latex} />
          {block.anchorLabel ? <span className={styles.eqno}>{block.anchorLabel}</span> : null}
        </div>
      );
    case 'table':
      return (
        <figure className={cls} data-block={block.id}>
          <table className={styles.table}>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr key={ri}>
                  {row.cells.map((cell, ci) =>
                    cell.isHeader ? (
                      <th key={ci} colSpan={cell.colspan} rowSpan={cell.rowspan}>
                        {renderInlineMath(cell.text)}
                      </th>
                    ) : (
                      <td key={ci} colSpan={cell.colspan} rowSpan={cell.rowspan}>
                        {renderInlineMath(cell.text)}
                      </td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {caption(block.anchorLabel, block.caption)}
        </figure>
      );
    case 'figure': {
      const asset = assetsById.get(block.assetRef.assetId);
      return (
        <figure className={`${cls} ${styles.figure}`} data-block={block.id}>
          {asset?.url ? (
            // eslint-disable-next-line @next/next/no-img-element -- signed S3 url, not a static asset
            <img src={asset.url} alt={block.caption ?? block.anchorLabel ?? '그림'} loading="lazy" />
          ) : null}
          {caption(block.anchorLabel, block.caption)}
        </figure>
      );
    }
    case 'list':
      return block.ordered ? (
        <ol className={cls} data-block={block.id}>
          {block.items.map((it, i) => (
            <li key={i}>{renderInlineMath(it.text)}</li>
          ))}
        </ol>
      ) : (
        <ul className={cls} data-block={block.id}>
          {block.items.map((it, i) => (
            <li key={i}>{renderInlineMath(it.text)}</li>
          ))}
        </ul>
      );
    case 'code':
      return (
        <pre className={`${cls} ${styles.code}`} data-block={block.id}>
          <code>{block.text}</code>
        </pre>
      );
  }
}

function caption(label?: string, text?: string) {
  if (!label && !text) return null;
  return (
    <figcaption className={styles.caption}>
      {label ? <strong>{label}</strong> : null}
      {label && text ? ' ' : null}
      {text ? renderInlineMath(text) : null}
    </figcaption>
  );
}

// ---- helpers ------------------------------------------------------------

interface TocEntry {
  id: string;
  title: string;
  depth: number;
}

function flattenToc(sections: DocSection[], depth = 1, out: TocEntry[] = []): TocEntry[] {
  for (const s of sections) {
    out.push({ id: s.id, title: s.title, depth });
    if (s.sections?.length) flattenToc(s.sections, depth + 1, out);
  }
  return out;
}

function isActive(block: DocBlock, anchor?: AnchorVM | null): boolean {
  if (!anchor) return false;
  const label = 'anchorLabel' in block ? block.anchorLabel : undefined;
  return Boolean(label && anchor.label && label === anchor.label);
}

function findBlockIdByLabel(doc: DocModel, label: string): string | null {
  if (!label) return null;
  const walk = (sections: DocSection[]): string | null => {
    for (const s of sections) {
      for (const b of s.blocks) {
        const l = 'anchorLabel' in b ? b.anchorLabel : undefined;
        if (l && l === label) return b.id;
      }
      const nested = s.sections ? walk(s.sections) : null;
      if (nested) return nested;
    }
    return null;
  };
  return walk(doc.sections);
}

function cssEscape(value: string): string {
  return value.replace(/["\\]/g, '\\$&');
}
