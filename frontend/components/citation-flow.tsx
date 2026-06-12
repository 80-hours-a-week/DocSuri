"use client";

// U4 진입점 — "인용 흐름 보기" Drawer 오버레이 (검색 컨텍스트 유지, E-C3 결정).
// 렌더 분기(graph|list)는 백엔드 FormFactorRouter의 결정(view.render)을 소비만 한다.
// 노드/항목 선택 → 데스크톱: 우측 사이드 패널 / 모바일: 중첩 바텀시트 (TRACE-01 AC).

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { X } from "lucide-react";

import { CitationGraph } from "@/components/citation-graph";
import { CitationList } from "@/components/citation-list";
import { PaperCard } from "@/components/paper-card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Label } from "@/components/ui/label";
import { fetchCitations } from "@/lib/citation-api";
import type { CitationPaper, CitationResponse, SearchResultPaper } from "@/lib/types";

function toCardPaper(paper: CitationPaper) {
  // PaperCard 재사용 (component-model §6.3·6.4) — difficulty는 U1 검색 전용 메타라 없음.
  return {
    id: paper.id,
    title: paper.title,
    authors: paper.authors,
    year: paper.year,
    citations: paper.citations,
    similarity: paper.similarity,
  };
}

// 데스크톱 분기(사이드 패널 vs 바텀시트) — SSR 안전한 미디어쿼리 구독.
const DESKTOP_QUERY = "(min-width: 768px)";
function subscribeDesktop(onChange: () => void) {
  const mql = window.matchMedia(DESKTOP_QUERY);
  mql.addEventListener("change", onChange);
  return () => mql.removeEventListener("change", onChange);
}
function useIsDesktop(): boolean {
  return useSyncExternalStore(
    subscribeDesktop,
    () => window.matchMedia(DESKTOP_QUERY).matches,
    () => false,
  );
}

export function CitationFlow({
  paper,
  onClose,
}: {
  paper: SearchResultPaper | null;
  onClose: () => void;
}) {
  const [resp, setResp] = useState<CitationResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<CitationPaper | null>(null);
  // TRACE-02 시연용 로컬 토글 — 전역 페르소나 모드는 U2 라운드 소유.
  const [undergrad, setUndergrad] = useState(false);
  const desktop = useIsDesktop();
  // 로딩은 파생값 — effect 본문의 동기 setState 회피 (react-hooks/set-state-in-effect).
  const loading = paper !== null && resp === null && error === null;

  // 경쟁 상태 가드 — 최신 요청의 응답만 반영 (U1 search-experience의 reqId 전례,
  // u4-code-review U4-M1). 닫기 시에도 증가시켜 늦게 도착한 응답을 폐기한다.
  const reqId = useRef(0);

  // setState는 promise 콜백 안에서만 — effect 동기 구간에 setState 없음
  // (react-hooks/set-state-in-effect 준수, 로딩 표시는 위 파생값).
  const load = useCallback((target: SearchResultPaper, asUndergrad: boolean) => {
    const id = ++reqId.current;
    const started = performance.now();
    fetchCitations(target, window.innerWidth, asUndergrad ? "undergrad" : undefined)
      .then((result) => {
        if (id !== reqId.current) return; // 더 새 요청 있음 — 폐기
        setResp(result);
        setError(null);
        setLatencyMs(Math.round(performance.now() - started));
      })
      .catch((e: unknown) => {
        if (id !== reqId.current) return;
        setResp(null);
        setError(e instanceof Error ? e.message : "인용 흐름 조회 중 오류가 발생했습니다.");
      });
  }, []);

  // 열림·토글 변경 시 조회 — 상태 초기화는 handleClose(이벤트 핸들러)에서 수행.
  useEffect(() => {
    if (!paper) return;
    load(paper, undergrad);
  }, [paper, undergrad, load]);

  const handleClose = useCallback(() => {
    reqId.current += 1; // 진행 중 요청 무효화 — 닫힌 뒤 도착한 응답이 상태를 되살리지 못하게
    setResp(null);
    setSelected(null);
    setUndergrad(false);
    setLatencyMs(null);
    setError(null);
    onClose();
  }, [onClose]);

  const empty =
    resp !== null && resp.view.outgoing.length === 0 && resp.view.incoming.length === 0;

  return (
    <Drawer open={paper !== null} onOpenChange={(open) => !open && handleClose()}>
      <DrawerContent className="h-[94vh]">
        <div className="relative mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden">
          <DrawerHeader className="shrink-0 text-left">
            <DrawerTitle className="line-clamp-1 pr-10">
              인용 흐름 — {paper?.title}
            </DrawerTitle>
            <DrawerDescription className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>
                직접 인용(참고 문헌)과 피인용(후속 연구) 1-hop
                {latencyMs !== null && ` · 조회 ${latencyMs}ms`}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Checkbox
                  id="undergrad-view"
                  checked={undergrad}
                  onCheckedChange={(v) => setUndergrad(v === true)}
                />
                <Label htmlFor="undergrad-view" className="text-xs font-normal">
                  학부 모드(후속 영향 Top-3)로 보기
                </Label>
              </span>
            </DrawerDescription>
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-3 top-3 size-11"
              aria-label="인용 흐름 닫기"
              onClick={handleClose}
            >
              <X className="size-5" aria-hidden />
            </Button>
          </DrawerHeader>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-6">
            {loading && (
              <div className="h-[60vh] animate-pulse rounded-xl bg-muted" aria-busy />
            )}

            {error && (
              <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-sm">
                <p className="font-medium text-destructive">{error}</p>
                <p className="mt-1 text-muted-foreground">
                  네트워크 상태를 확인한 뒤 다시 시도해 보세요.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 h-11"
                  onClick={() => {
                    setError(null); // 스켈레톤 복귀 후 재시도
                    if (paper) load(paper, undergrad);
                  }}
                >
                  다시 시도
                </Button>
              </div>
            )}

            {!loading && !error && empty && (
              // R4 폴백 빈 상태 — 다음 행동 제안 (NFR-NET-03·UX-04)
              <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
                <p className="font-medium">인용 정보를 가져오지 못했습니다.</p>
                <p className="mt-1 text-sm">
                  외부 인용 데이터가 일시적으로 응답하지 않을 수 있어요. 잠시 후 다시
                  시도하거나, arXiv 원문에서 참고 문헌을 확인해 보세요.
                </p>
              </div>
            )}

            {!loading && !error && resp && !empty && (
              resp.view.render === "graph" ? (
                <CitationGraph view={resp.view} onOpenPaper={setSelected} />
              ) : (
                <CitationList
                  view={resp.view}
                  topInfluence={resp.top_influence}
                  undergrad={undergrad}
                  onOpenPaper={setSelected}
                />
              )
            )}
          </div>

          {/* 데스크톱: 우측 사이드 패널 (TRACE-01 AC) */}
          {desktop && selected && (
            <aside
              className="absolute inset-y-0 right-0 z-10 w-96 overflow-y-auto border-l bg-background p-4 shadow-lg"
              aria-label="선택한 논문 카드"
            >
              <div className="mb-2 flex justify-end">
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-11"
                  aria-label="논문 카드 닫기"
                  onClick={() => setSelected(null)}
                >
                  <X className="size-5" aria-hidden />
                </Button>
              </div>
              <PaperCard paper={toCardPaper(selected)} />
            </aside>
          )}
        </div>

        {/* 모바일: 중첩 바텀시트 (TRACE-01 모바일 AC) */}
        {!desktop && (
          <Drawer open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
            <DrawerContent>
              <DrawerHeader className="sr-only">
                <DrawerTitle>선택한 논문 카드</DrawerTitle>
                <DrawerDescription>인용 흐름에서 선택한 논문의 상세 카드</DrawerDescription>
              </DrawerHeader>
              <div className="px-4 pb-8 pt-2">
                {selected && <PaperCard paper={toCardPaper(selected)} />}
              </div>
            </DrawerContent>
          </Drawer>
        )}
      </DrawerContent>
    </Drawer>
  );
}
