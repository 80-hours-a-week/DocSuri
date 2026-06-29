"""FR-17 figure/table extraction + image normalization (display-only, best-effort).

Hybrid extraction (BR-23, Q2=C): arXiv e-print (LaTeX) graphics when available, else a
PDF page-crop fallback. Permissive licenses only (TD-11/13 amended away from PyMuPDF/AGPL):
``pypdfium2`` (render), ``pdfplumber`` (layout/captions), ``Pillow`` (WebP normalize).

Pure helpers (``caption_kind``, ``finalize_assets``) are deterministic and unit/PBT tested
(P7). PDF/e-print parsing is import-guarded and exercised in Build & Test (env-gated).
"""

from __future__ import annotations

import io
import re
from collections.abc import Sequence

from .domain.assets import (
    AssetCropSpec,
    ExtractedAsset,
    FigureTableAsset,
    RawAssetCandidate,
    asset_id,
)
from .domain.enums import AssetSourceMode, AssetType

# Caption detection — "Figure 1", "Fig. 2", "Table 3" (case-insensitive, line start).
_CAPTION_RE = re.compile(r"^\s*(figure|fig\.?|table)\s+\d+", re.IGNORECASE)

_ASSETS_EXTRA_MISSING = "multimodal assets extra not installed (pip install .[assets])"

# Decompression-bomb guards for e-print image members (TD-15): cap per-image and per-tarball
# decoded bytes so a hostile tar member can't inflate unbounded before the pixel guard runs.
_MAX_IMAGE_BYTES = 20_000_000
_MAX_EPRINT_IMAGE_TOTAL = 200_000_000


def caption_kind(text: str) -> AssetType | None:
    """Classify a text line as a figure/table caption, or None. Pure (P7)."""
    match = _CAPTION_RE.match(text or "")
    if not match:
        return None
    head = match.group(1).lower()
    return AssetType.TABLE if head.startswith("table") else AssetType.FIGURE


# Strip a leading "Figure 3:" / "Fig. 2 -" label, then reduce to a comparable alphanumeric key.
_FIG_LABEL_RE = re.compile(r"^\s*(?:figure|fig\.?|table|tab\.?)\s*\d+\s*[:.\-—]?\s*", re.IGNORECASE)


def _caption_key(text: str) -> str:
    """Normalized caption key for matching doc-model figures to extracted assets.

    Drops the label prefix (numbering differs between sources) and non-alphanumerics, lowercased
    and length-capped, so a page-crop caption ("Figure 1: The Transformer …") matches the HTML
    figure caption ("The Transformer - model architecture."). Empty when there is nothing to key.
    """
    if not text:
        return ""
    stripped = _FIG_LABEL_RE.sub("", text)
    return re.sub(r"[^a-z0-9]", "", stripped.lower())[:48]


def figure_caption_anchors(doc_model: object | None) -> tuple[tuple[int, str], ...]:
    """(ordinal, caption-key) for each FigureBlock in a doc-model, for asset-id alignment.

    Walks figure blocks only (those with an ``id``), never their nested ``assetRef`` (which also
    carries ``type="figure"``, so a naive type scan double-counts). Returns () with no doc-model.
    """
    if doc_model is None:
        return ()
    data = doc_model.model_dump(by_alias=True) if hasattr(doc_model, "model_dump") else doc_model
    out: list[tuple[int, str]] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "figure" and "id" in node:
                ref = node.get("assetRef") or {}
                ordinal = ref.get("ordinal")
                if isinstance(ordinal, int):
                    caption = node.get("caption") or ref.get("caption") or ""
                    out.append((ordinal, _caption_key(caption)))
                return  # do not descend into the figure's assetRef
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(data)
    return tuple(out)


def _match_figure_ordinals(
    figures: Sequence[RawAssetCandidate],
    anchors: Sequence[tuple[int, str]] | None,
) -> list[int]:
    """Assign a doc-model figure ordinal to each (page,y,x)-ordered figure candidate.

    Caption-match against ``anchors`` first; any unmatched figure takes the lowest still-free
    ordinal, so the result is a collision-free permutation. No anchors -> positional (the legacy
    behavior, kept for tables and the captionless e-print path).
    """
    n = len(figures)
    if not anchors:
        return list(range(n))
    by_key: dict[str, int] = {}
    for ordinal, key in anchors:
        if key and key not in by_key:
            by_key[key] = ordinal
    result: list[int | None] = [None] * n
    taken: set[int] = set()
    for i, cand in enumerate(figures):
        ordinal = by_key.get(_caption_key(cand.caption))
        if ordinal is not None and ordinal not in taken:
            result[i] = ordinal
            taken.add(ordinal)
    nxt = 0
    for i in range(n):
        if result[i] is None:
            while nxt in taken:
                nxt += 1
            result[i] = nxt
            taken.add(nxt)
    return [o for o in result if o is not None]


def finalize_assets(
    paper_id: str,
    version: int,
    candidates: Sequence[RawAssetCandidate],
    *,
    figure_anchors: Sequence[tuple[int, str]] | None = None,
) -> tuple[ExtractedAsset, ...]:
    """Order candidates deterministically and assign per-type ordinals + asset ids (P7).

    Ordering is (page, y, x). Table ordinals are positional. FIGURE ordinals are caption-matched
    to the doc-model's figure blocks when ``figure_anchors`` ((ordinal, caption-key) per figure)
    is supplied, so a stored asset lands on the FigureBlock that references it even when the
    extraction order (e-print filename / page position) differs from HTML reading order. Without
    anchors, figures stay positional. Pure — same inputs always yield the same assets/ids (P7).
    """
    ordered = sorted(candidates, key=lambda c: (c.page, c.y, c.x, c.type.value))
    fig_ordinals = _match_figure_ordinals(
        [c for c in ordered if c.type is AssetType.FIGURE], figure_anchors
    )
    table_counter = 0
    fig_i = 0
    out: list[ExtractedAsset] = []
    for cand in ordered:
        if cand.type is AssetType.FIGURE:
            ordinal = fig_ordinals[fig_i]
            fig_i += 1
        else:
            ordinal = table_counter
            table_counter += 1
        meta = FigureTableAsset(
            asset_id=asset_id(paper_id, version, cand.type, ordinal),
            paper_id=paper_id,
            version=version,
            type=cand.type,
            ordinal=ordinal,
            source_mode=cand.source_mode,
            caption=cand.caption,
            section_ref=cand.section_ref,
            page_ref=cand.page,
            bbox=cand.bbox,
        )
        out.append(ExtractedAsset(meta=meta, image=cand.image))
    return tuple(out)


class ImageNormalizer:
    """Re-encode external images to WebP with bomb/size guards (TD-13/15, BR-24).

    Always re-decodes through a trusted decoder and re-encodes — original bytes are never
    stored or served. Returns None for undecodable / oversized images (asset is skipped).
    """

    def __init__(
        self,
        *,
        max_longest_side: int = 2048,
        max_pixels: int = 30_000_000,
        webp_quality: int = 80,
    ) -> None:
        self._max_side = max_longest_side
        self._max_pixels = max_pixels
        self._quality = webp_quality

    def normalize(self, raw: bytes) -> bytes | None:
        if not raw:
            return None
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - assets extra not installed
            raise RuntimeError(_ASSETS_EXTRA_MISSING) from exc
        try:
            with Image.open(io.BytesIO(raw)) as img:
                width, height = img.size
                if width * height > self._max_pixels:  # decompression-bomb guard
                    return None
                img = img.convert("RGB")
                longest = max(width, height)
                if longest > self._max_side:
                    scale = self._max_side / longest
                    img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))))
                out = io.BytesIO()
                img.save(out, format="WEBP", quality=self._quality)  # strips metadata
                return out.getvalue()
        except Exception:  # noqa: BLE001 - any decode/encode failure → skip this asset
            return None


class AssetExtractor:
    """Extract figure/table assets for a paper (hybrid, best-effort).

    Returns an empty tuple on any failure — the caller treats assets as non-blocking
    (BR-27). The ``source`` port supplies PDF / e-print bytes lazily (only for NEW|CHANGED
    papers, per the application wiring), so DUPLICATE papers incur no asset fetch (BR-22).
    """

    def __init__(self, *, normalizer: ImageNormalizer | None = None) -> None:
        self._normalizer = normalizer or ImageNormalizer()

    def extract(
        self,
        *,
        paper_id: str,
        version: int,
        pdf: bytes | None,
        eprint: bytes | None,
        figure_anchors: Sequence[tuple[int, str]] | None = None,
    ) -> tuple[ExtractedAsset, ...]:
        candidates: list[RawAssetCandidate] = []
        # Figures: prefer e-print structured graphics (original quality); fall back to crop.
        if eprint:
            candidates.extend(self._structured_figures(eprint))
        if pdf:
            # Tables always page-crop (TD-12); figures page-crop when e-print yielded none.
            want_figures = not candidates
            candidates.extend(self._page_crop(pdf, want_figures=want_figures))
        # figure_anchors aligns figure ordinals to the doc-model's FigureBlocks by caption, so
        # the stored asset id matches the block that references it (page-crop carries captions;
        # the captionless e-print path falls back to positional order — see _match_figure_ordinals).
        return finalize_assets(paper_id, version, candidates, figure_anchors=figure_anchors)

    # ---- hybrid paths (import-guarded; integration-tested in Build & Test) ----

    def _structured_figures(self, eprint: bytes) -> list[RawAssetCandidate]:
        """Extract raster graphics from an e-print tarball as figure candidates."""
        import tarfile

        out: list[RawAssetCandidate] = []
        try:
            budget = _MAX_EPRINT_IMAGE_TOTAL
            with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:*") as tar:
                members = sorted(
                    (m for m in tar.getmembers() if m.isfile()), key=lambda m: m.name
                )
                for member in members:
                    if not member.name.lower().endswith((".png", ".jpg", ".jpeg")):
                        continue
                    # Skip a member whose declared size is oversized, and stop once the per-tarball
                    # decoded budget is spent (decompression-bomb guard, TD-15).
                    if member.size > _MAX_IMAGE_BYTES or budget <= 0:
                        continue
                    fh = tar.extractfile(member)
                    if fh is None:
                        continue
                    # Bounded read — a lying tar header can't OOM us past the per-image cap.
                    raw = fh.read(_MAX_IMAGE_BYTES + 1)
                    if len(raw) > _MAX_IMAGE_BYTES:
                        continue
                    budget -= len(raw)
                    image = self._normalizer.normalize(raw)
                    if image is None:
                        continue
                    out.append(
                        RawAssetCandidate(
                            type=AssetType.FIGURE,
                            image=image,
                            source_mode=AssetSourceMode.STRUCTURED,
                            x=float(len(out)),
                        )
                    )
        except Exception:  # noqa: BLE001 - best-effort; fall back to page-crop
            return []
        return out

    def _page_crop(self, pdf: bytes, *, want_figures: bool) -> list[RawAssetCandidate]:
        """Render figure/table regions from a PDF, anchored to detected captions."""
        try:
            import pdfplumber
            import pypdfium2 as pdfium
        except ImportError as exc:  # pragma: no cover - assets extra not installed
            raise RuntimeError(_ASSETS_EXTRA_MISSING) from exc

        out: list[RawAssetCandidate] = []
        try:
            pdfium_doc = pdfium.PdfDocument(pdf)
            with pdfplumber.open(io.BytesIO(pdf)) as plumber:
                for page_no, page in enumerate(plumber.pages):
                    for line in page.extract_text_lines() or []:
                        kind = caption_kind(line.get("text", ""))
                        if kind is None or (kind is AssetType.FIGURE and not want_figures):
                            continue
                        bbox = _caption_region(page, line, kind)
                        image = _render_bbox_to_png(pdfium_doc, page_no, bbox, plumber_page=page)
                        image = self._normalizer.normalize(image) if image else None
                        if image is None:
                            continue
                        out.append(
                            RawAssetCandidate(
                                type=kind,
                                image=image,
                                source_mode=AssetSourceMode.PAGE_CROP,
                                caption=line.get("text", "").strip(),
                                section_ref=None,
                                page=page_no,
                                y=float(line.get("top", 0.0)),
                                x=float(line.get("x0", 0.0)),
                                bbox=bbox,
                            )
                        )
        except Exception:  # noqa: BLE001 - best-effort; skip assets for this paper
            return []
        return out


def _caption_region(page, line, kind) -> tuple[float, float, float, float]:
    """Heuristic region for a captioned figure/table: the band above the caption for a
    figure, below it for a table (tables typically sit under their caption)."""
    top = float(line.get("top", 0.0))
    page_h = float(page.height)
    if kind is AssetType.TABLE:
        return (0.0, top, float(page.width), min(page_h, top + page_h * 0.4))
    return (0.0, max(0.0, top - page_h * 0.4), float(page.width), top)


def _render_bbox_to_png(
    pdfium_doc, page_no: int, bbox, *, plumber_page=None
) -> bytes | None:
    """Render the bbox region of a page to PNG bytes via pypdfium2 (points-space bbox -> pixels).

    The page size in PDF points comes from ``plumber_page`` when the caller has a pdfplumber page
    (HTML/caption-region path) and from ``page.get_size()`` otherwise (TEI/GROBID coords path) —
    the only thing that differs between the two callers. The bbox is clamped to the rendered
    bitmap so an over-range coordinate can't yield an empty/oversized crop."""
    try:
        page = pdfium_doc[page_no]
        bitmap = page.render(scale=2.0)
        pil = bitmap.to_pil()
        if plumber_page is not None:
            width_pt, height_pt = plumber_page.width, plumber_page.height
        else:
            width_pt, height_pt = page.get_size()
        scale_x = pil.width / float(width_pt)
        scale_y = pil.height / float(height_pt)
        box = (
            max(0, int(bbox[0] * scale_x)),
            max(0, int(bbox[1] * scale_y)),
            min(pil.width, int(bbox[2] * scale_x)),
            min(pil.height, int(bbox[3] * scale_y)),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        out = io.BytesIO()
        pil.crop(box).save(out, format="PNG")
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return None


def crop_assets_from_specs(
    pdf: bytes,
    specs: Sequence[AssetCropSpec],
    *,
    paper_id: str,
    version: int,
    normalizer: ImageNormalizer | None = None,
) -> tuple[ExtractedAsset, ...]:
    """Render TEI-coordinate page-crops into stored assets (PDF/GROBID path, FR-17).

    Each spec's bbox (PDF points, top-left origin) is rendered from the PDF and normalized to
    WebP, keyed by the spec's ``asset_id`` — the SAME id the doc-model block references, so the
    image lands on the right FormulaBlock/FigureBlock (ordinal alignment guaranteed upstream).
    Best-effort: any failure yields an empty tuple (assets never block indexing, BR-27).
    """
    if not specs:
        return ()
    normalizer = normalizer or ImageNormalizer()
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - assets extra not installed
        raise RuntimeError(_ASSETS_EXTRA_MISSING) from exc

    out: list[ExtractedAsset] = []
    try:
        doc = pdfium.PdfDocument(pdf)
        page_count = len(doc)
        for spec in specs:
            page_idx = spec.page - 1  # GROBID coords are 1-based
            if page_idx < 0 or page_idx >= page_count:
                continue
            raw = _render_bbox_to_png(doc, page_idx, spec.bbox)
            image = normalizer.normalize(raw) if raw else None
            if image is None:
                continue
            meta = FigureTableAsset(
                asset_id=spec.asset_id,
                paper_id=paper_id,
                version=version,
                type=spec.type,
                ordinal=spec.ordinal,
                source_mode=AssetSourceMode.PAGE_CROP,
                caption=spec.caption,
                page_ref=spec.page,
                bbox=spec.bbox,
            )
            out.append(ExtractedAsset(meta=meta, image=image))
    except Exception:  # noqa: BLE001 - best-effort; skip assets for this paper
        return ()
    return tuple(out)


