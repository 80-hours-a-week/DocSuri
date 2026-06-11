"use client";

// 결과 카드 — NFR-UX-03: 데스크톱(≥768px) 6메타 1뷰 / 모바일 3메타 + "더 보기" 펼침.
// 우선 메타(항상 노출): 제목·연도·유사도. 펼침 메타: 저자·인용수·난이도.

import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { DifficultyLabel, SearchResultPaper } from "@/lib/types";

const DIFFICULTY_STYLE: Record<DifficultyLabel, string> = {
  입문: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  중급: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  고급: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200",
};

export function PaperCard({ paper }: { paper: SearchResultPaper }) {
  const [expanded, setExpanded] = useState(false);
  const arxivUrl = `https://arxiv.org/abs/${paper.id}`;
  const similarityPct = Math.round(paper.similarity * 100);

  return (
    <Card>
      <CardContent className="p-4 sm:p-5">
        <a
          href={arxivUrl}
          target="_blank"
          rel="noreferrer"
          className="group inline-flex items-start gap-1.5 font-semibold leading-snug hover:underline"
        >
          <span>{paper.title}</span>
          <ExternalLink className="mt-1 size-3.5 shrink-0 opacity-60 group-hover:opacity-100" aria-hidden />
        </a>

        {/* 우선 메타 — 항상 노출 (모바일 3메타) */}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span>{paper.year}</span>
          <span aria-hidden>·</span>
          <span>유사도 {similarityPct}%</span>
        </div>

        {/* 펼침 메타 — 데스크톱 항상 / 모바일 펼침 시 (저자·인용수·난이도) */}
        <div className={`${expanded ? "block" : "hidden"} md:block`}>
          <div className="mt-2 space-y-1 text-sm text-muted-foreground">
            <p className="line-clamp-1">{paper.authors.join(", ")}</p>
            <div className="flex items-center gap-3">
              <span>인용 {paper.citations.toLocaleString("en-US")}</span>
              <Badge className={DIFFICULTY_STYLE[paper.difficulty]} variant="secondary">
                {paper.difficulty}
              </Badge>
            </div>
          </div>
        </div>

        {/* 모바일 전용 더보기 토글 (≥44px 터치 타깃) */}
        <Button
          variant="ghost"
          size="sm"
          className="mt-2 h-11 w-full justify-center text-muted-foreground md:hidden"
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? (
            <>접기 <ChevronUp className="size-4" aria-hidden /></>
          ) : (
            <>더 보기 <ChevronDown className="size-4" aria-hidden /></>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
