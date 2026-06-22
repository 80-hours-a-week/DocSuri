'use client';

// AssetGallery (FR-17, BR-SF-9/11) — renders a paper's figure/table assets in the detail
// page. Images load from short-lived signed URLs (SEC-9); captions are escaped by React
// (BR-SF-9). Mobile-first: lazy-loaded, responsive, with a reserved frame to avoid layout
// shift. A figure/table summary anchor ("출처 보기") highlights + scrolls to its asset
// (matchAssetForAnchor). License-disallowed / empty → the section renders nothing.
import { useEffect, useMemo, useRef } from 'react';
import type { AnchorVM, AssetRef } from '@/types/generated';
import { useAssets } from '@/lib/useAssets';
import { matchAssetForAnchor } from '@/lib/assetAnchor';
import { StateView } from './StateView';
import styles from './AssetGallery.module.css';

interface AssetGalleryProps {
  paperId: string;
  version: number;
  /** The currently selected summary anchor; figure/table anchors scroll to their asset. */
  anchor?: AnchorVM | null;
}

export function AssetGallery({ paperId, version, anchor }: AssetGalleryProps) {
  const { state, load } = useAssets();
  const refs = useRef<Map<string, HTMLElement>>(new Map());

  useEffect(() => {
    void load(paperId, version);
  }, [load, paperId, version]);

  const assets = useMemo<AssetRef[]>(
    () => (state.status === 'done' && state.outcome.kind === 'assets' ? state.outcome.assets : []),
    [state],
  );
  const activeId = useMemo(() => matchAssetForAnchor(assets, anchor), [assets, anchor]);

  useEffect(() => {
    if (!activeId) return;
    refs.current.get(activeId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [activeId]);

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

  return (
    <section className={styles.root} aria-label="그림·도표" data-testid="asset-gallery">
      <h2 className={styles.heading}>그림·도표</h2>
      <ul className={styles.grid}>
        {outcome.assets.map((a) => (
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
            <figure className={styles.figure}>
              <div className={styles.frame}>
                {/* eslint-disable-next-line @next/next/no-img-element -- signed S3 URL, not a static asset */}
                <img className={styles.img} src={a.url} alt={a.caption} loading="lazy" />
              </div>
              <figcaption className={styles.caption}>{a.caption}</figcaption>
            </figure>
          </li>
        ))}
      </ul>
    </section>
  );
}
