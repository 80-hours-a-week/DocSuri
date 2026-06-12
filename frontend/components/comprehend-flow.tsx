"use client";

// U2 진입점 — "요약 보기" Drawer (u2_ui_build_plan B2·B3).
// COMP-01·03: 전문/학부 모드 요약(4섹션) · COMP-02: 섹션 접기 + 세션 기본값
// (sessionStorage) · COMP-04: 초록 드래그/롱프레스 선택 번역(데스크톱 인접
// 패널/모바일 바텀시트). 모드 토글은 화면 로컬 — 전역 페르소나는 후속 라운드.

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Languages, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { fetchSummary, fetchTranslation } from "@/lib/comprehend-api";
import { useIsDesktop } from "@/lib/use-is-desktop";
import type {
  Persona,
  SearchResultPaper,
  SectionKey,
  SummaryResponse,
  TranslationResult,
} from "@/lib/types";

const SECTION_LABELS: Record<SectionKey, string> = {
  question: "연구 질문",
  method: "방법",
  result: "결과",
  limit: "한계",
};
const SECTION_ORDER: SectionKey[] = ["question", "method", "result", "limit"];
const COLLAPSED_KEY = "docsuri-summary-collapsed"; // COMP-02 — 세션 내 기본값
const LONG_PRESS_MS = 500; // COMP-04 모바일 AC

function readCollapsedDefaults(): Record<SectionKey, boolean> {
  const fallback = { question: false, method: false, result: false, limit: false };
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.sessionStorage.getItem(COLLAPSED_KEY);
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback;
  } catch {
    return fallback;
  }
}

export function ComprehendFlow({
  paper,
  onClose,
}: {
  paper: SearchResultPaper | null;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<Persona>("pro");
  const [resp, setResp] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [collapsed, setCollapsed] = useState<Record<SectionKey, boolean>>(readCollapsedDefaults);
  const [selectedText, setSelectedText] = useState("");
  const [translation, setTranslation] = useState<TranslationResult | null>(null);
  const [translating, setTranslating] = useState(false);
  const desktop = useIsDesktop();
  const abstractRef = useRef<HTMLParagraphElement | null>(null);
  const touchStartedAt = useRef(0);
  const reqId = useRef(0); // 경쟁 상태 가드 (U4-M1 전례)

  const loading = paper !== null && resp === null && error === null;

  const load = useCallback((paperId: string, asMode: Persona) => {
    const id = ++reqId.current;
    const started = performance.now();
    fetchSummary(paperId, asMode)
      .then((result) => {
        if (id !== reqId.current) return;
        setResp(result);
        setError(null);
        setLatencyMs(Math.round(performance.now() - started));
      })
      .catch((e: unknown) => {
        if (id !== reqId.current) return;
        setResp(null);
        setError(e instanceof Error ? e.message : "요약 생성 중 오류가 발생했습니다.");
      });
  }, []);

  useEffect(() => {
    if (!paper) return;
    load(paper.id, mode);
  }, [paper, mode, load]);

  const handleClose = useCallback(() => {
    reqId.current += 1;
    setResp(null);
    setError(null);
    setLatencyMs(null);
    setMode("pro");
    setSelectedText("");
    setTranslation(null);
    onClose();
  }, [onClose]);

  // COMP-02 — 토글 + 세션 기본값 저장 (다음 요약에도 적용)
  const toggleSection = (key: SectionKey) => {
    setCollapsed((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        window.sessionStorage.setItem(COLLAPSED_KEY, JSON.stringify(next));
      } catch {
        /* 저장 불가 환경 — 토글 자체는 동작 */
      }
      return next;
    });
  };

  // COMP-04 — 선택 캡처 (데스크톱 드래그 / 모바일 ≥500ms 롱프레스)
  const captureSelection = () => {
    const sel = window.getSelection();
    const text = sel?.toString().trim() ?? "";
    if (!text || !abstractRef.current) return;
    if (!sel?.anchorNode || !abstractRef.current.contains(sel.anchorNode)) return;
    setSelectedText(text.slice(0, 2000));
  };
  const onTouchStart = () => {
    touchStartedAt.current = performance.now();
  };
  const onTouchEnd = () => {
    if (performance.now() - touchStartedAt.current >= LONG_PRESS_MS) {
      // 네이티브 선택 핸들 반영 직후 읽는다
      setTimeout(captureSelection, 50);
    }
  };

  const translate = () => {
    if (!selectedText || translating) return;
    setTranslating(true);
    fetchTranslation(selectedText, desktop ? "desktop" : "mobile")
      .then((result) => {
        setTranslation(result);
        setError(null);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "번역 중 오류가 발생했습니다.");
      })
      .finally(() => setTranslating(false));
  };

  const summary = resp?.summary;
  const readability = resp?.readability;

  return (
    <Drawer open={paper !== null} onOpenChange={(open) => !open && handleClose()}>
      <DrawerContent className="h-[94vh]">
        <div className="mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden">
          <DrawerHeader className="relative shrink-0 text-left">
            <DrawerTitle className="line-clamp-1 pr-10">요약 — {paper?.title}</DrawerTitle>
            <DrawerDescription className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>
                연구 질문·방법·결과·한계 4섹션
                {latencyMs !== null && summary && (
                  <> · 조회 {latencyMs}ms · 토큰 {summary.cost.tokens_in}/{summary.cost.tokens_out}</>
                )}
              </span>
              <span className="inline-flex overflow-hidden rounded-lg border" role="group" aria-label="요약 모드">
                {(["pro", "undergrad"] as const).map((m) => (
                  <Button
                    key={m}
                    variant={mode === m ? "default" : "ghost"}
                    size="sm"
                    className="h-9 rounded-none px-3"
                    aria-pressed={mode === m}
                    onClick={() => {
                      if (mode !== m) {
                        setResp(null); // 모드 전환 — 스켈레톤 후 재조회 (이벤트 핸들러)
                        setMode(m);
                      }
                    }}
                  >
                    {m === "pro" ? "전문 모드" : "학부 모드"}
                  </Button>
                ))}
              </span>
            </DrawerDescription>
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-3 top-3 size-11"
              aria-label="요약 닫기"
              onClick={handleClose}
            >
              <X className="size-5" aria-hidden />
            </Button>
          </DrawerHeader>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-6">
            {loading && <div className="h-[60vh] animate-pulse rounded-xl bg-muted" aria-busy />}

            {error && (
              <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-sm">
                <p className="font-medium text-destructive">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 h-11"
                  onClick={() => {
                    setError(null);
                    if (paper) load(paper.id, mode);
                  }}
                >
                  다시 시도
                </Button>
              </div>
            )}

            {!loading && !error && summary && (
              <div className="space-y-5">
                {/* 4섹션 — COMP-01·02 */}
                <section className="space-y-2">
                  {SECTION_ORDER.map((key) => (
                    <div key={key} className="rounded-xl border">
                      <button
                        type="button"
                        className="flex min-h-11 w-full items-center gap-2 px-3 py-2 text-left font-medium"
                        aria-expanded={!collapsed[key]}
                        onClick={() => toggleSection(key)}
                      >
                        {collapsed[key] ? (
                          <ChevronRight className="size-4 shrink-0" aria-hidden />
                        ) : (
                          <ChevronDown className="size-4 shrink-0" aria-hidden />
                        )}
                        {SECTION_LABELS[key]}
                      </button>
                      {!collapsed[key] && (
                        <p className="px-3 pb-3 text-sm leading-relaxed text-muted-foreground">
                          {summary.sections[key]}
                        </p>
                      )}
                    </div>
                  ))}
                </section>

                {/* 어휘 풀이 + 가독성 (학부) */}
                {summary.vocab_explanations.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {summary.vocab_explanations.map((v) => (
                      <Badge key={v.term} variant="secondary">
                        {v.term} → {v.ko}
                      </Badge>
                    ))}
                  </div>
                )}
                {mode === "undergrad" && readability && (
                  <p className="text-xs text-muted-foreground">
                    가독성: 평균 {readability.metrics.average_eojeol_per_sentence.toFixed(1)}어절/문장 ·{" "}
                    {readability.passed ? "학부 기준 통과" : "기준 초과(재작성 시도됨)"}
                  </p>
                )}

                {/* 영문 초록 + 선택 번역 — COMP-04 */}
                <section className={desktop && translation ? "grid grid-cols-2 gap-4" : "space-y-3"}>
                  <div className="rounded-xl border p-3">
                    <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
                      영문 초록 — {desktop ? "드래그로 선택" : "길게 눌러 선택"} 후 번역
                    </h3>
                    <p
                      ref={abstractRef}
                      className="select-text text-sm leading-relaxed"
                      onMouseUp={captureSelection}
                      onTouchStart={onTouchStart}
                      onTouchEnd={onTouchEnd}
                    >
                      {resp.paper.abstract}
                    </p>
                    <Button
                      size="sm"
                      className="mt-3 h-11"
                      disabled={!selectedText || translating}
                      onClick={translate}
                    >
                      <Languages className="size-4" aria-hidden />
                      {translating ? "번역 중…" : selectedText ? "선택한 부분 번역" : "먼저 본문을 선택하세요"}
                    </Button>
                  </div>

                  {/* 데스크톱: 인접 패널 (COMP-04 AC) */}
                  {desktop && translation && (
                    <div className="rounded-xl border bg-muted/30 p-3" aria-live="polite">
                      <h3 className="mb-2 text-sm font-semibold text-muted-foreground">한국어 번역</h3>
                      <p className="text-sm leading-relaxed">{translation.target_text}</p>
                      {translation.glossary_hits.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {translation.glossary_hits.map((v) => (
                            <Badge key={v.term} variant="outline">
                              {v.term} → {v.ko}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </section>
              </div>
            )}
          </div>
        </div>

        {/* 모바일: 번역 결과 바텀시트 (COMP-04 모바일 AC) */}
        {!desktop && (
          <Drawer open={translation !== null} onOpenChange={(open) => !open && setTranslation(null)}>
            <DrawerContent>
              <DrawerHeader className="text-left">
                <DrawerTitle>한국어 번역</DrawerTitle>
                <DrawerDescription className="sr-only">선택한 본문의 번역 결과</DrawerDescription>
              </DrawerHeader>
              <div className="px-4 pb-8">
                <p className="text-sm leading-relaxed">{translation?.target_text}</p>
                {translation && translation.glossary_hits.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {translation.glossary_hits.map((v) => (
                      <Badge key={v.term} variant="outline">
                        {v.term} → {v.ko}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </DrawerContent>
          </Drawer>
        )}
      </DrawerContent>
    </Drawer>
  );
}
