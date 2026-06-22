'use client';

// PersonaToggle (US-S4, Q4=A, BR-SF-6) — summary-only level segmented control.
// Switching re-requests with the chosen persona; an already-generated level is a
// cache hit (instant, no extra cost). Not shown for translation (single).
import type { Persona } from '@/types/generated';
import styles from './PersonaToggle.module.css';

interface PersonaToggleProps {
  value: Persona;
  onChange: (persona: Persona) => void;
}

const OPTIONS: { value: Persona; label: string }[] = [
  { value: 'expert', label: '전문가용' },
  { value: 'beginner', label: '입문자용' },
];

export function PersonaToggle({ value, onChange }: PersonaToggleProps) {
  return (
    <div className={styles.root} role="radiogroup" aria-label="요약 수준">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={value === o.value ? styles.active : styles.option}
          onClick={() => onChange(o.value)}
          data-testid={`persona-${o.value}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
