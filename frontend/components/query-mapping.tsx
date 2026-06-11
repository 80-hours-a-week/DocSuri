"use client";

// 한→영 매핑 1줄 — US-DISC-04 ("입력 한국어가 영문 키워드로 어떻게 매핑되었는지 1줄로 표시").

import { Languages } from "lucide-react";

import type { QueryMapping } from "@/lib/types";

export function QueryMappingNote({ mapping }: { mapping: QueryMapping | null }) {
  if (!mapping) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg bg-muted/60 px-3 py-2 text-sm text-muted-foreground">
      <Languages className="mt-0.5 size-4 shrink-0" aria-hidden />
      <p>{mapping.explanation}</p>
    </div>
  );
}
