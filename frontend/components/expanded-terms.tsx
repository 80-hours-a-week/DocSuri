"use client";

// 확장 키워드 칩 — US-DISC-03. 체크/해제 시 즉시 재검색(상위에서 트리거).

import type { ExpandedTerm } from "@/lib/types";

interface ExpandedTermsProps {
  terms: ExpandedTerm[];
  selected: string[];
  onToggle: (term: string) => void;
}

export function ExpandedTerms({ terms, selected, onToggle }: ExpandedTermsProps) {
  if (terms.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-xs text-muted-foreground">확장 키워드 — 선택하면 즉시 다시 검색합니다</p>
      <ul className="flex flex-wrap gap-2">
        {terms.map((t) => {
          const checked = selected.includes(t.term);
          return (
            <li key={t.term}>
              <button
                type="button"
                role="switch"
                aria-checked={checked}
                onClick={() => onToggle(t.term)}
                className={`inline-flex min-h-9 items-center rounded-full border px-3 py-1 text-sm transition-colors ${
                  checked
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
              >
                {t.term}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
