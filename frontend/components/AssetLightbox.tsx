'use client';

// AssetLightbox (FR-17) — full-size viewer for a figure/table opened from the gallery.
// Mobile-first rationale: figures/tables are unreadable at thumbnail size, so the real
// viewing happens here at full size with ‹이전/다음› navigation. Accessibility:
// role="dialog" aria-modal, Escape + backdrop close, ArrowLeft/Right navigation, initial
// focus, body-scroll lock while open. Signed S3 URL only (SEC-9); caption escaped by
// React (BR-SF-9).
import { useEffect, useRef } from 'react';
import type { AssetRef } from '@/types/generated';
import styles from './AssetLightbox.module.css';

interface AssetLightboxProps {
  assets: readonly AssetRef[];
  /** Index of the asset currently shown. */
  index: number;
  /** Navigate to another index (clamped by the caller's bounds checks). */
  onIndex: (index: number) => void;
  onClose: () => void;
}

export function AssetLightbox({ assets, index, onIndex, onClose }: AssetLightboxProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const asset = assets[index];
  const hasPrev = index > 0;
  const hasNext = index < assets.length - 1;

  // Escape closes; arrows navigate within bounds. Body-scroll lock + initial focus.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft' && index > 0) onIndex(index - 1);
      else if (e.key === 'ArrowRight' && index < assets.length - 1) onIndex(index + 1);
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panelRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [index, assets.length, onClose, onIndex]);

  if (!asset) return null;

  return (
    <div className={styles.backdrop} onClick={onClose} data-testid="asset-lightbox-backdrop">
      <div
        ref={panelRef}
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-label={asset.caption}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        data-testid="asset-lightbox"
      >
        <div className={styles.head}>
          <span className={styles.counter} data-testid="asset-lightbox-counter">
            {index + 1} / {assets.length}
          </span>
          <button
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label="닫기"
            data-testid="asset-lightbox-close"
          >
            ✕
          </button>
        </div>

        <div className={styles.stage}>
          <button
            type="button"
            className={styles.nav}
            onClick={() => onIndex(index - 1)}
            disabled={!hasPrev}
            aria-label="이전 그림·도표"
            data-testid="asset-lightbox-prev"
          >
            ‹
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element -- signed S3 URL, not a static asset */}
          <img
            className={styles.img}
            src={asset.url}
            alt={asset.caption}
            data-testid="asset-lightbox-img"
          />
          <button
            type="button"
            className={styles.nav}
            onClick={() => onIndex(index + 1)}
            disabled={!hasNext}
            aria-label="다음 그림·도표"
            data-testid="asset-lightbox-next"
          >
            ›
          </button>
        </div>

        <figcaption className={styles.caption}>{asset.caption}</figcaption>
      </div>
    </div>
  );
}
