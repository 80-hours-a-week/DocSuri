"use client";

// U4 CitationListView — 모바일(<768px)·학부 모드 간소화 리스트 (NFR-MOBILE-05).
// TRACE-01 모바일: "중심/인용/피인용" 3섹션 + 제목·저자 즉시 필터 + 1탭 카드 열기(≥44px).
// TRACE-02 학부: 피인용 가중 Top-3 카드만 — 그래프·다른 섹션 미표시 (인지 부담 최소화).

import { useState } from "react";
import { PanelRightOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CitationPaper, CitationView } from "@/lib/types";

function Row({
  paper,
  onOpen,
}: {
  paper: CitationPaper;
  onOpen: (paper: CitationPaper) => void;
}) {
  return (
    <li className="flex items-center gap-2 rounded-lg border px-3 py-2">
      <div className="min-w-0 flex-1 text-sm">
        <p className="line-clamp-2 font-medium leading-snug">{paper.title}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {paper.year || "—"} · 인용 {paper.citations.toLocaleString("en-US")}
          {paper.authors.length > 0 && ` · ${paper.authors[0]}${paper.authors.length > 1 ? " 외" : ""}`}
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        className="h-11 shrink-0"
        aria-label={`논문 카드 열기: ${paper.title}`}
        onClick={() => onOpen(paper)}
      >
        <PanelRightOpen className="size-4" aria-hidden />
        <span className="sr-only sm:not-sr-only sm:ml-1">카드 열기</span>
      </Button>
    </li>
  );
}

function Section({
  title,
  papers,
  onOpen,
}: {
  title: string;
  papers: CitationPaper[];
  onOpen: (paper: CitationPaper) => void;
}) {
  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
        {title} <span className="font-normal">({papers.length})</span>
      </h3>
      {papers.length === 0 ? (
        <p className="rounded-lg border border-dashed px-3 py-2 text-sm text-muted-foreground">
          해당 항목이 없습니다.
        </p>
      ) : (
        <ul className="space-y-2">
          {papers.map((p) => (
            <Row key={p.id} paper={p} onOpen={onOpen} />
          ))}
        </ul>
      )}
    </section>
  );
}

export function CitationList({
  view,
  topInfluence,
  undergrad,
  onOpenPaper,
}: {
  view: CitationView;
  topInfluence: CitationPaper[];
  undergrad: boolean;
  onOpenPaper: (paper: CitationPaper) => void;
}) {
  const [filter, setFilter] = useState("");

  const q = filter.trim().toLowerCase();
  const match = (p: CitationPaper) =>
    !q ||
    p.title.toLowerCase().includes(q) ||
    p.authors.some((a) => a.toLowerCase().includes(q));

  // TRACE-02 — 학부 모드: 후속 영향 Top-3만, 그래프·기타 섹션 없음.
  if (undergrad) {
    return (
      <div className="space-y-3" data-testid="citation-top3">
        <Section title="이 논문이 영향을 준 후속 논문 Top 3" papers={topInfluence} onOpen={onOpenPaper} />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="citation-list">
      <Input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="제목·저자로 즉시 필터"
        aria-label="인용 목록 필터"
        className="h-11"
      />
      <Section title="중심" papers={[view.center].filter(match)} onOpen={onOpenPaper} />
      <Section title="인용 (이 논문이 참고)" papers={view.outgoing.filter(match)} onOpen={onOpenPaper} />
      <Section title="피인용 (이 논문을 인용)" papers={view.incoming.filter(match)} onOpen={onOpenPaper} />
    </div>
  );
}
