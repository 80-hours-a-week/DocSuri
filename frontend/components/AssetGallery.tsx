'use client';

// AssetGallery (FR-17, BR-SF-9/11) — renders a paper's figure/table assets as a compact
// thumbnail grid (3 per row on mobile, 4 on desktop). Mobile rationale: figures/tables are
// too small to read inline and large inline images bury the body, so thumbnails stay
// compact and the real viewing happens in AssetLightbox on tap. Thumbnails load from
// short-lived signed URLs (SEC-9), lazily, with a reserved aspect-ratio frame to avoid
// layout shift; captions are escaped by React (BR-SF-9). A figure/table summary anchor
// ("출처 보기") scrolls to its thumbnail and opens it large (matchAssetForAnchor).
// License-disallowed / empty → the section renders nothing.
import { useEffect, useMemo, useRef, useState } from 'react';
import type { AnchorVM, AssetRef } from '@/types/generated';
import { useAssets } from '@/lib/useAssets';
import { matchAssetForAnchor } from '@/lib/assetAnchor';
import { StateView } from './StateView';
import { AssetLightbox } from './AssetLightbox';
import styles from './AssetGallery.module.css';

interface AssetGalleryProps {
  paperId: string;
  version: number;
  /** The currently selected summary anchor; figure/table anchors open their asset. */
  anchor?: AnchorVM | null;
}

export function AssetGallery({ paperId, version, anchor }: AssetGalleryProps) {
  const { state, load } = useAssets();
  const refs = useRef<Map<string, HTMLElement>>(new Map());
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    void load(paperId, version);
  }, [load, paperId, version]);

  const assets = useMemo<AssetRef[]>(
    () => (state.status === 'done' && state.outcome.kind === 'assets' ? state.outcome.assets : []),
    [state],
  );
  const activeId = useMemo(() => matchAssetForAnchor(assets, anchor), [assets, anchor]);

  // A figure/table "출처 보기" anchor scrolls to its thumbnail and opens it at full size —
  // the point of the anchor is to see the evidence figure, so we surface it directly.
  useEffect(() => {
    if (!activeId) return;
    const idx = assets.findIndex((a) => a.assetId === activeId);
    if (idx < 0) return;
    refs.current.get(activeId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setOpenIndex(idx);
  }, [activeId, assets]);

  if (state.status === 'loading' || state.status === 'idle') {
    return <StateView kind="loading" title="그림·도표 불러오는 중…" message="잠시만 기다려 주세요." />;
  }
  const { outcome } = state;
  if (outcome.kind === 'error') {
    return (
      <StateView
        kind="error"
        message="그림·도표를 불러올 수 없어요."
        onRetry={() => void load(paperId, version)}
      />
    );
  }
  // license_unavailable / unauthorized / empty → render nothing (no clutter; the detail
  // page already surfaces license state for the full text).
  if (outcome.kind !== 'assets' || outcome.assets.length === 0) return null;

  const items = outcome.assets;

  return (
    <section className={styles.root} aria-label="그림·도표" data-testid="asset-gallery">
      <h2 className={styles.heading}>
        그림·도표 <span className={styles.count}>{items.length}</span>
      </h2>
      <ul className={styles.grid}>
        {items.map((a, i) => (
          <li
            key={a.assetId}
            ref={(el) => {
              if (el) refs.current.set(a.assetId, el);
              else refs.current.delete(a.assetId);
            }}
            className={a.assetId === activeId ? `${styles.item} ${styles.active}` : styles.item}
            data-testid="asset-item"
            data-asset-type={a.type}
          >
            <button
              type="button"
              className={styles.thumb}
              onClick={() => setOpenIndex(i)}
              aria-haspopup="dialog"
              aria-label={`${a.caption} — 크게 보기`}
            >
              <span className={styles.thumbFrame}>
                {/* eslint-disable-next-line @next/next/no-img-element -- signed S3 URL, not a static asset */}
                <img
                  className={styles.thumbImg}
                  src={a.url}
                  alt=""
                  loading="lazy"
                  data-testid="asset-thumb-img"
                />
              </span>
              <span className={styles.thumbCaption}>{a.caption}</span>
            </button>
          </li>
        ))}
      </ul>

      {openIndex != null ? (
        <AssetLightbox
          assets={items}
          index={openIndex}
          onIndex={setOpenIndex}
          onClose={() => setOpenIndex(null)}
        />
      ) : null}
    </section>
  );
}
