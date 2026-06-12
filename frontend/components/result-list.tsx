"use client";

// 결과 목록 — 상위 20 카드 렌더. 빈 상태에 다음 행동 제안 (NFR-UX-04).

import type { ReactNode } from "react";

import type { SearchResultPaper } from "@/lib/types";
import { PaperCard } from "./paper-card";

interface ResultListProps {
  papers: SearchResultPaper[];
  loading: boolean;
  searched: boolean;
  /** 카드 하단 액션 주입 — U4 "인용 흐름 보기" 등 (paper-card footer 패스스루). */
  renderFooter?: (paper: SearchResultPaper) => ReactNode;
}

export function ResultList({ papers, loading, searched, renderFooter }: ResultListProps) {
  if (loading) {
    return (
      <div className="space-y-3" aria-busy>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  if (searched && papers.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
        <p className="font-medium">검색 결과가 없습니다.</p>
        <p className="mt-1 text-sm">연도·분야 필터를 넓히거나 다른 검색어로 다시 시도해 보세요.</p>
      </div>
    );
  }

  if (!searched) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
        <p className="font-medium">연구 의도를 자연어로 입력해 보세요.</p>
        <p className="mt-1 text-sm">예: &ldquo;transformer-based retrieval-augmented summarization&rdquo; 또는 &ldquo;트랜스포머가 뭔가요&rdquo;</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground" aria-live="polite">
        상위 {papers.length}건
      </p>
      {papers.map((p) => (
        <PaperCard key={p.id} paper={p} footer={renderFooter?.(p)} />
      ))}
    </div>
  );
}
