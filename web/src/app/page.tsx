"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { DBPaper } from "@/lib/apis/types";

// ─────────────────────────────────────────────────────────────
// PaperCard
// ─────────────────────────────────────────────────────────────
function PaperCard({
  paper,
  inLibrary,
  onToggleLibrary,
}: {
  paper: DBPaper & { pdf_url?: string | null; added_at?: string; tags?: string[] };
  inLibrary: boolean;
  onToggleLibrary: (paper: DBPaper) => void;
}) {
  const authors =
    (paper.authors?.slice(0, 3).map((a) => a.name).join(", ") ?? "") +
    (paper.authors?.length > 3 ? " 외" : "");

  const pdfHref =
    paper.pdf_url ??
    (paper.arxiv_id ? `https://arxiv.org/pdf/${paper.arxiv_id}` : null);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-col gap-3 hover:border-indigo-500 transition-colors">
      <div className="flex items-center gap-2 flex-wrap">
        {paper.year && (
          <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">
            {paper.year}
          </span>
        )}
        {paper.citation_count > 0 && (
          <span className="text-xs bg-indigo-900/60 text-indigo-300 px-2 py-0.5 rounded-full">
            인용 {paper.citation_count.toLocaleString()}
          </span>
        )}
        {paper.similarity_score !== undefined && (
          <span className="text-xs bg-emerald-900/60 text-emerald-300 px-2 py-0.5 rounded-full">
            유사도 {(paper.similarity_score * 100).toFixed(1)}%
          </span>
        )}
      </div>

      <h2 className="text-white font-semibold text-base leading-snug line-clamp-2">
        {paper.title}
      </h2>

      {authors && <p className="text-gray-400 text-xs">{authors}</p>}

      {paper.abstract && (
        <p className="text-gray-400 text-sm leading-relaxed line-clamp-3">
          {paper.abstract}
        </p>
      )}

      <div className="flex items-center gap-2 mt-auto pt-2">
        {pdfHref && (
          <a
            href={pdfHref}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg transition-colors"
          >
            PDF 보기
          </a>
        )}
        {paper.id && (
          <button
            onClick={() => onToggleLibrary(paper)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              inLibrary
                ? "border-rose-500 text-rose-400 hover:bg-rose-500/10"
                : "border-gray-600 text-gray-400 hover:border-indigo-400 hover:text-indigo-300"
            }`}
          >
            {inLibrary ? "저장 취소" : "＋ 저장"}
          </button>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────
type Tab  = "explore" | "library";
type Mode = "ai-fallback" | "ai-vector" | "search" | "empty";
type Sort = "citation" | "recent";

export default function Home() {
  const [tab,    setTab]    = useState<Tab>("explore");
  const [papers, setPapers] = useState<(DBPaper & { pdf_url?: string | null })[]>([]);
  const [libraryPapers, setLibraryPapers] = useState<(DBPaper & { added_at?: string })[]>([]);
  const [loading,        setLoading]        = useState(false);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [query,  setQuery]  = useState("");
  const [sort,   setSort]   = useState<Sort>("citation");
  const [mode,   setMode]   = useState<Mode>("ai-fallback");
  const [aiReason, setAiReason] = useState<string>("");
  const [userId, setUserId] = useState("");
  const [libraryIds, setLibraryIds] = useState<Set<number>>(new Set());
  const [error,  setError]  = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── userId 초기화 ─────────────────────────────────────────
  useEffect(() => {
    let id = localStorage.getItem("userId");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("userId", id);
    }
    setUserId(id);
  }, []);

  // ── 라이브러리 ID 목록 로드 ───────────────────────────────
  const fetchLibraryIds = useCallback((uid: string) => {
    fetch(`/api/library?userId=${uid}`)
      .then((r) => r.json())
      .then((d) => {
        const ids = new Set<number>(d.data?.map((p: DBPaper) => p.id) ?? []);
        setLibraryIds(ids);
      })
      .catch(() => {});
  }, []);

  // ── 라이브러리 논문 목록 로드 (라이브러리 탭용) ──────────
  const fetchLibraryPapers = useCallback(async (uid: string) => {
    setLibraryLoading(true);
    try {
      const res = await fetch(`/api/library?userId=${uid}`);
      const d   = await res.json();
      setLibraryPapers(d.data ?? []);
    } catch {
      // 무시
    } finally {
      setLibraryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (userId) fetchLibraryIds(userId);
  }, [userId, fetchLibraryIds]);

  // ── 탐색 탭: AI 추천 논문 목록 조회 ────────────────────
  const fetchPapers = useCallback(async (uid: string, _s: Sort) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (uid) params.set("userId", uid);
      const res  = await fetch(`/api/recommend?${params}`);
      if (!res.ok) throw new Error("추천 목록을 가져오지 못했습니다.");
      const data = await res.json();
      setPapers(data.data ?? []);
      setAiReason(data.reason ?? "");
      if (data.mode === "ai-vector") setMode("ai-vector");
      else if (data.mode === "empty") setMode("empty");
      else setMode("ai-fallback");
    } catch (e) {
      setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (userId) fetchPapers(userId, sort);
  }, [userId, sort, fetchPapers]);

  // ── 탭 전환 ──────────────────────────────────────────────
  const handleTabChange = (t: Tab) => {
    setTab(t);
    if (t === "library" && userId) fetchLibraryPapers(userId);
  };

  // ── 외부 API 검색 ─────────────────────────────────────────
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setMode("search");
    try {
      const res  = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error("검색에 실패했습니다.");
      const data = await res.json();
      setPapers(data.data ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  // ── 라이브러리 토글 ───────────────────────────────────────
  const handleToggleLibrary = async (paper: DBPaper) => {
    if (!paper.id) return;
    const isIn = libraryIds.has(paper.id);

    // 낙관적 업데이트 (목록에서 제거하지 않고 버튼 상태만 변경)
    setLibraryIds((prev) => {
      const next = new Set(prev);
      isIn ? next.delete(paper.id) : next.add(paper.id);
      return next;
    });

    // 라이브러리 탭이 열려있으면 즉시 반영
    if (tab === "library") {
      if (isIn) {
        setLibraryPapers((prev) => prev.filter((p) => p.id !== paper.id));
      }
    }

    try {
      if (isIn) {
        await fetch(`/api/library?userId=${userId}&paperId=${paper.id}`, {
          method: "DELETE",
        });
      } else {
        await fetch("/api/library", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ userId, paperId: paper.id }),
        });
      }
    } catch {
      // 롤백
      setLibraryIds((prev) => {
        const next = new Set(prev);
        isIn ? next.add(paper.id) : next.delete(paper.id);
        return next;
      });
      if (tab === "library" && isIn) {
        fetchLibraryPapers(userId);
      }
    }
  };

  // ── 검색 초기화 ───────────────────────────────────────────
  const handleReset = () => {
    setQuery("");
    setAiReason("");
    inputRef.current?.focus();
    fetchPapers(userId, sort);
  };

  // ── 스켈레톤 ─────────────────────────────────────────────
  const Skeleton = () => (
    <div className="flex flex-col gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-gray-800 rounded-xl h-36 animate-pulse" />
      ))}
    </div>
  );

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-12 flex flex-col gap-8">

        {/* 헤더 */}
        <header className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold tracking-tight">📄 논문 추천</h1>
          <p className="text-gray-400 text-sm">
            arXiv · Semantic Scholar · OpenAlex 기반 논문 검색 및 개인화 추천
          </p>
        </header>

        {/* 탭 */}
        <div className="flex bg-gray-800/60 rounded-xl p-1 gap-1 text-sm">
          <button
            onClick={() => handleTabChange("explore")}
            className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
              tab === "explore"
                ? "bg-indigo-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            탐색
          </button>
          <button
            onClick={() => handleTabChange("library")}
            className={`flex-1 py-2 rounded-lg font-medium transition-colors relative ${
              tab === "library"
                ? "bg-indigo-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            내 라이브러리
            {libraryIds.size > 0 && (
              <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                tab === "library" ? "bg-white/20" : "bg-indigo-600 text-white"
              }`}>
                {libraryIds.size}
              </span>
            )}
          </button>
        </div>

        {/* ── 탐색 탭 ── */}
        {tab === "explore" && (
          <>
            {/* 검색창 */}
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="예: transformer, diffusion model, LLM..."
                className="flex-1 bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white px-5 py-3 rounded-xl text-sm font-medium transition-colors"
              >
                검색
              </button>
              {mode === "search" && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="border border-gray-600 hover:border-gray-400 text-gray-400 hover:text-white px-4 py-3 rounded-xl text-sm transition-colors"
                >
                  초기화
                </button>
              )}
            </form>

            {/* 모드 & 정렬 */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex flex-col gap-1">
                <div className="text-xs">
                  {mode === "ai-vector" && (
                    <span className="bg-emerald-900/50 text-emerald-300 border border-emerald-700 px-3 py-1 rounded-full">
                      ✦ AI 개인화 추천
                    </span>
                  )}
                  {mode === "ai-fallback" && (
                    <span className="bg-indigo-900/50 text-indigo-300 border border-indigo-700 px-3 py-1 rounded-full">
                      ✦ AI 추천 (인기 논문)
                    </span>
                  )}
                  {mode === "empty" && (
                    <span className="text-gray-500">논문이 없습니다</span>
                  )}
                  {mode === "search" && (
                    <span className="text-gray-500">
                      검색 결과 · {papers.length}건
                    </span>
                  )}
                </div>
                {aiReason && mode !== "search" && (
                  <p className="text-xs text-gray-400 italic">AI: {aiReason}</p>
                )}
              </div>
            </div>

            {/* 에러 */}
            {error && (
              <div className="bg-rose-900/40 border border-rose-700 text-rose-300 rounded-xl px-4 py-3 text-sm">
                {error}
              </div>
            )}

            {/* 논문 목록 */}
            {loading ? (
              <Skeleton />
            ) : papers.length === 0 ? (
              <div className="text-center text-gray-500 py-20">
                {mode === "search"
                  ? "검색 결과가 없습니다."
                  : "논문이 없습니다. 먼저 검색해 보세요."}
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {papers.map((paper, i) => (
                  <PaperCard
                    key={paper.id ?? `${paper.arxiv_id}-${i}`}
                    paper={paper}
                    inLibrary={paper.id ? libraryIds.has(paper.id) : false}
                    onToggleLibrary={handleToggleLibrary}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* ── 라이브러리 탭 ── */}
        {tab === "library" && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                저장한 논문 {libraryIds.size}편
              </p>
              {libraryIds.size > 0 && (
                <span className="text-xs text-gray-500">
                  저장 논문 기반으로 개인화 추천이 활성화됩니다
                </span>
              )}
            </div>

            {libraryLoading ? (
              <Skeleton />
            ) : libraryPapers.length === 0 ? (
              <div className="text-center text-gray-500 py-20 flex flex-col gap-3">
                <p>저장된 논문이 없어요.</p>
                <p className="text-xs">탐색 탭에서 논문을 저장하면 이곳에 표시되고,<br />개인화 추천이 활성화됩니다.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {libraryPapers.map((paper, i) => (
                  <PaperCard
                    key={paper.id ?? i}
                    paper={paper}
                    inLibrary={true}
                    onToggleLibrary={handleToggleLibrary}
                  />
                ))}
              </div>
            )}
          </>
        )}

      </div>
    </main>
  );
}
