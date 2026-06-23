// FR-17 anchor → asset matching (inception Q5, FR-12). A summary anchor with
// target=figure|table is linked to a rendered AssetRef so "출처 보기" scrolls to the
// figure/table. Pure + deterministic (unit-tested) — no DOM access here.
import type { AssetRef, AnchorVM } from '@/types/generated';

/** Extract the caption number from "Figure 1" / "Fig. 2" / "Table 3" / a bare label. */
export function captionNumber(text: string | undefined): number | null {
  if (!text) return null;
  const m = text.match(/(?:figure|fig\.?|table)\s*(\d+)/i) ?? text.match(/(\d+)/);
  return m ? Number(m[1]) : null;
}

/** Return the assetId an anchor points at, or null. Matches a figure/table anchor to an
 * asset by (1) same type + same caption number, else (2) type + 1-based ordinal. */
export function matchAssetForAnchor(
  assets: readonly AssetRef[],
  anchor: Pick<AnchorVM, 'target' | 'label'> | null | undefined,
): string | null {
  if (!anchor || (anchor.target !== 'figure' && anchor.target !== 'table')) return null;
  const type = anchor.target;
  const num = captionNumber(anchor.label);
  if (num != null) {
    const byNumber = assets.find((a) => a.type === type && captionNumber(a.caption) === num);
    if (byNumber) return byNumber.assetId;
    const byType = assets.filter((a) => a.type === type);
    const byOrdinal = byType[num - 1];
    if (byOrdinal) return byOrdinal.assetId;
  }
  const first = assets.find((a) => a.type === type);
  return first ? first.assetId : null;
}
