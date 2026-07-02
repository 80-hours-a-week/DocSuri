'use client';

import { useEffect, useRef, useState } from 'react';
import type { AssetRef, TranslationVM } from '@/types/generated';
import { useGlossaryTerms } from '@/lib/useGlossaryTerms';
import { GlossaryTermBadge } from './GlossaryTermBadge';
import { DocModelBody } from './DocModelViewer';
import styles from './TranslationView.module.css';

// TranslationView (US-S2, BR-SF-9 / BR-S18) — Korean translation rendered as a "translated
// doc-model": the SAME structured rich view as the original body (sections·수식·표·그림), only the
// text is Korean. Below it, the glossary is split into two groups (BR-S4):
//   · 표준 용어 — DocSuri standard seed terms present in this paper. Both keep-as-is (English) chips
//     and mapping (en→ko) chips are tappable to save a STRONG override (re-generates the
//     translation); a mapping chip pre-fills its editor with the standard rendering.
//   · 원어 유지 용어 — the other terms the model kept in English; tappable to save a WEAK rendering
//     (read-time, no re-translation).
// External text is escaped by React. No anchors (translation is grounding-free). This view owns the
// "which term's editor is open" state so only one is open at a time; a click outside closes it.

// Stable empty map so an abstract translation (no figures) doesn't re-create one each render.
const NO_ASSETS: Map<string, AssetRef> = new Map();

interface TranslationViewProps {
  translation: TranslationVM;
  cached?: boolean;
  /** Show the personal-glossary editor. Only the full-text translation (본문 번역) exposes it. */
  showGlossary?: boolean;
  /** Signed figure/table asset urls (by assetId) for figures inside the translated doc-model.
   * Omitted for abstract translation (no figures). */
  assetsById?: Map<string, AssetRef>;
}

export function TranslationView({
  translation,
  showGlossary = false,
  assetsById,
}: TranslationViewProps) {
  const [openTerm, setOpenTerm] = useState<string | null>(null);
  const termsRef = useRef<HTMLDivElement | null>(null);
  const { terms, setTerm } = useGlossaryTerms();

  // Close the open editor on any pointer-down outside the glossary section. `pointerdown` covers
  // both mouse and touch (a plain `mousedown` may not fire on a real phone), and fires before click
  // so a tap elsewhere dismisses before it activates anything.
  useEffect(() => {
    if (openTerm === null) return;
    const onPointerDown = (e: PointerEvent) => {
      if (termsRef.current && !termsRef.current.contains(e.target as Node)) {
        setOpenTerm(null);
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [openTerm]);

  // Split the glossary: standard keep-as-is (editable → strong) and standard mappings (editable →
  // strong, pre-filled) both go under 표준 용어; the remaining kept terms (editable → weak) go under
  // 원어 유지 용어. `nonStandardKept` excludes EVERY standard term — keep-as-is AND mapping — so a
  // kept term the model also mapped can't render twice (which would open two editors for one term).
  // Terms are compared case-insensitively.
  const standardGlossary = translation.standardGlossary ?? [];
  const standardKeepAsIs = standardGlossary.filter((g) => !g.translated);
  const standardMappings = standardGlossary.filter((g) => g.translated);
  const standardTerms = new Set(standardGlossary.map((g) => g.term.toLowerCase()));
  const nonStandardKept = translation.keptTerms.filter((t) => !standardTerms.has(t.toLowerCase()));
  const hasStandard = standardKeepAsIs.length > 0 || standardMappings.length > 0;
  const hasGlossary = showGlossary && (hasStandard || nonStandardKept.length > 0);

  return (
    <div className={styles.root} data-testid="translation-view">
      {translation.docModel.meta.title ? (
        <h1 className={styles.paperTitle} data-testid="translation-title">
          {translation.docModel.meta.title}
        </h1>
      ) : null}

      {hasGlossary ? (
        <section className={styles.glossary} ref={termsRef} aria-label="용어집">
          {nonStandardKept.length > 0 ? (
            <div className={styles.group}>
              <h3 className={styles.glossaryTitle}>원어 유지 용어</h3>
              <p className={styles.glossaryHint}>
                번역에서 원어로 남은 용어예요. 탭해서 내 번역어를 지정하면 바로 반영돼요.
              </p>
              <div className={styles.terms}>
                {nonStandardKept.map((t) => (
                  <GlossaryTermBadge
                    key={`kept-${t}`}
                    term={t}
                    open={openTerm === t}
                    onOpen={() => setOpenTerm(t)}
                    onClose={() => setOpenTerm(null)}
                    saved={terms[t]}
                    onSaved={(termTo) => setTerm(t, termTo)}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {hasStandard ? (
            <div className={styles.group}>
              <h3 className={styles.glossaryTitle}>표준 용어</h3>
              <p className={styles.glossaryHint}>
                DocSuri가 표준으로 정한 용어예요. 바꾸면 전문 번역을 다시 만들어요.
              </p>
              <div className={styles.terms}>
                {standardKeepAsIs.map((g) => (
                  <GlossaryTermBadge
                    key={`std-${g.term}`}
                    term={g.term}
                    strong
                    open={openTerm === g.term}
                    onOpen={() => setOpenTerm(g.term)}
                    onClose={() => setOpenTerm(null)}
                    saved={terms[g.term]}
                    onSaved={(termTo) => setTerm(g.term, termTo)}
                  />
                ))}
                {standardMappings.map((g) => (
                  <GlossaryTermBadge
                    key={`map-${g.term}`}
                    term={g.term}
                    strong
                    defaultValue={g.translated}
                    open={openTerm === g.term}
                    onOpen={() => setOpenTerm(g.term)}
                    onClose={() => setOpenTerm(null)}
                    saved={terms[g.term]}
                    onSaved={(termTo) => setTerm(g.term, termTo)}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      <div className={styles.text}>
        <DocModelBody docModel={translation.docModel} assetsById={assetsById ?? NO_ASSETS} />
      </div>
    </div>
  );
}
