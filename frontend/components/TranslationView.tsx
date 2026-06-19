import type { TranslationVM } from '@/types/generated';
import styles from './TranslationView.module.css';

// TranslationView (US-S2, BR-SF-9) — Korean translation (abstract or full per
// scope) + kept-terms badges (untranslated terms kept as-is). External text is
// escaped by React. No anchors (translation is grounding-free). The scope label is
// not repeated here — the modal heading already names 초록/전문 번역.

interface TranslationViewProps {
  translation: TranslationVM;
  cached?: boolean;
}

export function TranslationView({ translation, cached }: TranslationViewProps) {
  return (
    <div className={styles.root} data-testid="translation-view">
      {cached ? (
        <span className={styles.cached} data-testid="translation-cached">
          저장된 결과
        </span>
      ) : null}

      {translation.keptTerms.length > 0 ? (
        <div className={styles.terms}>
          {translation.keptTerms.map((t, i) => (
            <span key={`${t}-${i}`} className={styles.term} title="원어 유지 용어">
              {t}
            </span>
          ))}
        </div>
      ) : null}

      <p className={styles.text}>{translation.koreanText}</p>
    </div>
  );
}
