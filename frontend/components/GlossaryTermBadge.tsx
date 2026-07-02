'use client';

// GlossaryTermBadge (개인 용어집) — a kept-term chip that opens a tiny inline editor to save the
// user's preferred Korean rendering via POST /api/glossary. `strong` (a 표준 용어 = seed keep-as-is)
// saves as a prompt-enforced override that re-generates the full translation; otherwise it is a
// weak read-time substitution. The chip shows only the term; a personalized chip is tinted (색:
// 미수정=파랑 / 내가 지정=주황) and the saved rendering pre-fills the editor input on open.
// Mock-first: getApiClient() routes to MockTransport in dev. Open state is CONTROLLED by the parent
// (TranslationView) so only one editor is open at a time. `term` is external data, escaped by React.
import { useEffect, useId, useRef, useState } from 'react';
import { getApiClient } from '@/lib/api';
import { UserFacingError } from '@/lib/api/errors';
import { recordGlossaryUpdated } from '@/lib/personalization';
import styles from './GlossaryTermBadge.module.css';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface GlossaryTermBadgeProps {
  term: string;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  /** True for a 표준 용어 (seed keep-as-is or mapping): saving overrides it as a strong,
   * prompt-enforced term that re-generates the full translation. False → weak read-time
   * substitution. */
  strong?: boolean;
  /** Standard rendering to pre-fill the editor when the user has no saved override yet — used for
   * mapping terms (e.g. attention → 어텐션) so the editor starts from the standard value. */
  defaultValue?: string;
  /** The user's previously saved rendering (undefined = none). Pre-fills the editor (over
   * ``defaultValue``) and marks the chip as personalized. */
  saved?: string;
  /** Notify the parent of a successful save so its term map stays in sync. */
  onSaved?: (termTo: string) => void;
}

export function GlossaryTermBadge({
  term,
  open,
  onOpen,
  onClose,
  strong = false,
  defaultValue = '',
  saved,
  onSaved,
}: GlossaryTermBadgeProps) {
  const [value, setValue] = useState('');
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const wasOpenRef = useRef(false);
  const panelId = useId();

  // Pre-fill with the saved rendering only on the open transition, then focus. A late-arriving
  // glossary fetch can change props while the editor is already open; re-running the pre-fill then
  // would clobber the user's in-progress draft, so we latch on open instead. On close: reset.
  useEffect(() => {
    if (open && !wasOpenRef.current) {
      setValue(saved ?? defaultValue);
      requestAnimationFrame(() => inputRef.current?.focus());
    } else if (!open) {
      setValue('');
      setStatus('idle');
      setErrMsg(null);
    }
    wasOpenRef.current = open;
  }, [open, saved, defaultValue]);

  const save = async () => {
    const termTo = value.trim();
    if (!termTo || status === 'saving') return;
    setStatus('saving');
    setErrMsg(null);
    try {
      const res = await getApiClient().upsertGlossaryTerm({
        termFrom: term,
        termTo,
        promptEnforced: strong,
      });
      recordGlossaryUpdated(res.glossaryVer);
      setStatus('saved');
      onSaved?.(termTo);
    } catch (e) {
      setErrMsg(e instanceof UserFacingError ? e.message : null);
      setStatus('error');
    }
  };

  return (
    <span className={styles.wrap}>
      <button
        type="button"
        className={styles.term}
        data-saved={saved ? 'true' : undefined}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => (open ? onClose() : onOpen())}
        title="탭하여 내 번역어 지정"
        data-testid="glossary-badge"
      >
        {term}
      </button>

      {open ? (
        <span
          id={panelId}
          className={styles.popover}
          role="group"
          aria-label={`${term} 번역어 지정`}
        >
          {status === 'saved' ? (
            <span className={styles.savedNote} role="status" data-testid="glossary-saved">
              {strong ? '저장됨 · 번역을 다시 만드는 중이에요' : '저장됨 · 바로 반영됐어요'}
            </span>
          ) : (
            <>
              <input
                ref={inputRef}
                className={styles.input}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void save();
                  if (e.key === 'Escape') onClose();
                }}
                placeholder={`${term} → 내 번역어`}
                aria-label={`${term}의 번역어`}
                maxLength={40}
                disabled={status === 'saving'}
                data-testid="glossary-input"
              />
              <button
                type="button"
                className={styles.save}
                onClick={() => void save()}
                disabled={!value.trim() || status === 'saving'}
                data-testid="glossary-save"
              >
                {status === 'saving' ? '저장 중…' : '저장'}
              </button>
            </>
          )}
          {status === 'error' ? (
            <span className={styles.error} role="alert">
              {errMsg ?? '저장 실패 · 다시 시도해 주세요'}
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}
