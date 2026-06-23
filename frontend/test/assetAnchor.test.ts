import { describe, it, expect } from 'vitest';
import { captionNumber, matchAssetForAnchor } from '@/lib/assetAnchor';
import type { AssetRef, AnchorVM } from '@/types/generated';

const assets: AssetRef[] = [
  { assetId: 'f0', type: 'figure', ordinal: 0, caption: 'Figure 1: arch', sourceMode: 'page-crop', url: 'u' },
  { assetId: 'f1', type: 'figure', ordinal: 1, caption: 'Figure 2: results', sourceMode: 'page-crop', url: 'u' },
  { assetId: 't0', type: 'table', ordinal: 0, caption: 'Table 1: scores', sourceMode: 'page-crop', url: 'u' },
];

const anchor = (target: string, label: string): AnchorVM =>
  ({ field: 'results', target, span: 's', label }) as AnchorVM;

describe('captionNumber', () => {
  it('reads figure/table/bare numbers', () => {
    expect(captionNumber('Figure 2: x')).toBe(2);
    expect(captionNumber('Fig. 3')).toBe(3);
    expect(captionNumber('Table 1')).toBe(1);
    expect(captionNumber('no number')).toBeNull();
    expect(captionNumber(undefined)).toBeNull();
  });
});

describe('matchAssetForAnchor', () => {
  it('matches by type + caption number', () => {
    expect(matchAssetForAnchor(assets, anchor('figure', 'Figure 2'))).toBe('f1');
    expect(matchAssetForAnchor(assets, anchor('table', 'Table 1'))).toBe('t0');
  });

  it('falls back to type + ordinal when no caption number matches', () => {
    // No "Figure 9" caption → 1-based ordinal 9 is out of range → first figure.
    expect(matchAssetForAnchor(assets, anchor('figure', 'unlabeled'))).toBe('f0');
  });

  it('returns null for non figure/table anchors and empty input', () => {
    expect(matchAssetForAnchor(assets, anchor('section', 'Section 2'))).toBeNull();
    expect(matchAssetForAnchor(assets, null)).toBeNull();
    expect(matchAssetForAnchor([], anchor('figure', 'Figure 1'))).toBeNull();
  });
});
