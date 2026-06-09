"use client";

import { useEffect, useState, useCallback, useRef } from "react";

interface Paper {
  id: number;
  arxiv_id: string | null;
  s2_paper_id: string | null;
  openalex_id: string | null;
  title: string;
  year: number | null;
  citation_count: number;
  has_embedding: boolean;
  status: string;
  created_at: string;
}

interface LibraryEntry {
  user_id: string;
  paper_id: number;
  paper_title: string;
  tags: string[];
  added_at: string;
}

interface DBSnapshot {
  papers: Paper[];
  library: LibraryEntry[];
  stats: { total: number; embedded: number; library: number };
}

interface QueryResult {
  rows: Record<string, unknown>[];
  fields: string[];
  rowCount: number;
  elapsed: number;
}

const PRESET_QUERIES = [
  {
    label: "논문 전체 (인용순)",
    sql: `SELECT id, arxiv_id, openalex_id,
  LEFT(title, 60) AS title,
  year, citation_count,
  embedding IS NOT NULL AS has_embedding,
  status
FROM papers
ORDER BY citation_count DESC;`,
  },
  {
    label: "임베딩 대기",
    sql: `SELECT id, LEFT(title, 60) AS title, status, created_at
FROM papers
WHERE embedding IS NULL
ORDER BY id;`,
  },
  {
    label: "라이브러리 전체",
    sql: `SELECT ul.user_id, ul.paper_id,
  LEFT(p.title, 60) AS title,
  ul.tags, ul.added_at
FROM user_library ul
JOIN papers p ON p.id = ul.paper_id
ORDER BY ul.added_at DESC;`,
  },
  {
    label: "유저별 저장 수",
    sql: `SELECT user_id, COUNT(*) AS saved_count
FROM user_library
GROUP BY user_id
ORDER BY saved_count DESC;`,
  },
  {
    label: "연도별 논문 수",
    sql: `SELECT year, COUNT(*) AS cnt
FROM papers
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year DESC;`,
  },
];

export default function AdminPage() {
  const [data,           setData]           = useState<DBSnapshot | null>(null);
  const [lastUpdated,    setLastUpdated]     = useState("");
  const [autoRefresh,    setAutoRefresh]     = useState(true);
  const [tab,            setTab]             = useState<"papers" | "library" | "sql">("papers");

  // SQL Editor
  const [sql,            setSql]             = useState(PRESET_QUERIES[0].sql);
  const [queryResult,    setQueryResult]     = useState<QueryResult | null>(null);
  const [queryError,     setQueryError]      = useState<string | null>(null);
  const [queryLoading,   setQueryLoading]    = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // DB 스냅샷 로드
  const load = useCallback(async () => {
    try {
      const res  = await fetch("/api/admin/db");
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date().toLocaleTimeString("ko-KR"));
    } catch { /* 무시 */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!autoRefresh || tab === "sql") return;
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [autoRefresh, tab, load]);

  // SQL 실행
  const runQuery = useCallback(async () => {
    const q = sql.trim();
    if (!q) return;
    setQueryLoading(true);
    setQueryError(null);
    setQueryResult(null);
    try {
      const res  = await fetch("/api/admin/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: q }),
      });
      const json = await res.json();
      if (!res.ok) setQueryError(json.error ?? "오류");
      else         setQueryResult(json);
    } catch (e) {
      setQueryError(e instanceof Error ? e.message : "오류");
    } finally {
      setQueryLoading(false);
    }
  }, [sql]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      runQuery();
    }
    if (e.key === "Tab") {
      e.preventDefault();
      const el    = textareaRef.current!;
      const start = el.selectionStart;
      const end   = el.selectionEnd;
      setSql(sql.slice(0, start) + "  " + sql.slice(end));
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 2;
      });
    }
  };

  const Skeleton = () => (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-8 bg-gray-800 rounded animate-pulse" />
      ))}
    </div>
  );

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6 font-mono text-sm">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">

        {/* 헤더 */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">🗄️ DB 뷰어</h1>
            <p className="text-gray-500 text-xs mt-0.5">paper_recommender</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-gray-500 text-xs">
              마지막 갱신: <span className="text-gray-300">{lastUpdated}</span>
            </span>
            <button
              onClick={() => setAutoRefresh((v) => !v)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                autoRefresh
                  ? "border-emerald-500 text-emerald-400"
                  : "border-gray-600 text-gray-500"
              }`}
            >
              {autoRefresh ? "● 자동갱신 ON" : "○ 자동갱신 OFF"}
            </button>
            <button
              onClick={load}
              className="text-xs px-3 py-1.5 rounded-lg border border-indigo-500 text-indigo-400 hover:bg-indigo-500/10 transition-colors"
            >
              새로고침
            </button>
          </div>
        </div>

        {/* 통계 카드 */}
        {data && (
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "전체 논문",      value: data.stats.total,    color: "text-indigo-400"  },
              { label: "임베딩 완료",    value: data.stats.embedded, color: "text-emerald-400" },
              { label: "라이브러리 저장", value: data.stats.library,  color: "text-amber-400"   },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex flex-col gap-1">
                <p className="text-gray-400 text-xs">{label}</p>
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>
        )}

        {/* 탭 */}
        <div className="flex bg-gray-800/60 rounded-xl p-1 gap-1 text-xs w-fit">
          {([
            { key: "papers",  label: `papers (${data?.stats.total ?? 0})` },
            { key: "library", label: `user_library (${data?.stats.library ?? 0})` },
            { key: "sql",     label: "SQL Editor" },
          ] as const).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-4 py-1.5 rounded-lg transition-colors ${
                tab === key ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── papers 탭 ── */}
        {tab === "papers" && (
          data ? (
            <div className="overflow-x-auto rounded-xl border border-gray-700">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-800 text-gray-400 text-left">
                    {["id","source_id","title","year","citation","embed","status","저장시각"].map((h) => (
                      <th key={h} className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.papers.map((p, i) => (
                    <tr key={p.id} className={`border-t border-gray-700/60 ${i % 2 === 0 ? "bg-gray-900" : "bg-gray-900/50"}`}>
                      <td className="px-3 py-2 text-gray-500">{p.id}</td>
                      <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                        {p.arxiv_id ?? p.s2_paper_id ?? p.openalex_id ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-white max-w-xs truncate">{p.title}</td>
                      <td className="px-3 py-2 text-gray-400">{p.year ?? "—"}</td>
                      <td className="px-3 py-2 text-indigo-300">{p.citation_count.toLocaleString()}</td>
                      <td className="px-3 py-2">
                        {p.has_embedding
                          ? <span className="text-emerald-400">✓</span>
                          : <span className="text-gray-600">✗</span>}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`px-1.5 py-0.5 rounded text-xs ${
                          p.status === "active"  ? "bg-emerald-900/50 text-emerald-400" :
                          p.status === "pending" ? "bg-amber-900/50 text-amber-400" :
                                                   "bg-rose-900/50 text-rose-400"
                        }`}>{p.status}</span>
                      </td>
                      <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{p.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Skeleton />
        )}

        {/* ── user_library 탭 ── */}
        {tab === "library" && (
          data ? (
            data.library.length === 0 ? (
              <div className="text-center text-gray-600 py-16">저장된 라이브러리 항목이 없습니다.</div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-700">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-800 text-gray-400 text-left">
                      {["user_id","paper_id","논문 제목","tags","저장시각"].map((h) => (
                        <th key={h} className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.library.map((entry, i) => (
                      <tr key={`${entry.user_id}-${entry.paper_id}`} className={`border-t border-gray-700/60 ${i % 2 === 0 ? "bg-gray-900" : "bg-gray-900/50"}`}>
                        <td className="px-3 py-2 text-gray-400 font-mono truncate max-w-[140px]">{entry.user_id}</td>
                        <td className="px-3 py-2 text-gray-500">{entry.paper_id}</td>
                        <td className="px-3 py-2 text-white max-w-sm truncate">{entry.paper_title}</td>
                        <td className="px-3 py-2 text-gray-500">{entry.tags.length > 0 ? entry.tags.join(", ") : "—"}</td>
                        <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{entry.added_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : <Skeleton />
        )}

        {/* ── SQL Editor 탭 ── */}
        {tab === "sql" && (
          <div className="flex flex-col gap-4">

            {/* 프리셋 버튼 */}
            <div className="flex flex-wrap gap-2">
              {PRESET_QUERIES.map((p) => (
                <button
                  key={p.label}
                  onClick={() => {
                    setSql(p.sql);
                    setQueryResult(null);
                    setQueryError(null);
                    textareaRef.current?.focus();
                  }}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-600 text-gray-400 hover:border-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* 에디터 */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                onKeyDown={handleKeyDown}
                spellCheck={false}
                rows={10}
                className="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-emerald-300 font-mono placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-y transition-colors leading-relaxed"
                placeholder="SELECT * FROM papers LIMIT 10;"
              />
              <div className="absolute bottom-3 right-3 flex items-center gap-2">
                <span className="text-gray-600 text-xs">⌘↵ 실행</span>
                <button
                  onClick={runQuery}
                  disabled={queryLoading || !sql.trim()}
                  className="text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg transition-colors"
                >
                  {queryLoading ? "실행 중…" : "▶ 실행"}
                </button>
              </div>
            </div>

            {/* 에러 */}
            {queryError && (
              <div className="bg-rose-900/30 border border-rose-700 text-rose-300 rounded-xl px-4 py-3 text-xs font-mono whitespace-pre-wrap">
                {queryError}
              </div>
            )}

            {/* 결과 */}
            {queryResult && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className="text-emerald-400">{queryResult.rowCount}행</span>
                  <span>·</span>
                  <span>{queryResult.elapsed}ms</span>
                </div>
                {queryResult.rows.length === 0 ? (
                  <div className="text-gray-600 text-xs py-6 text-center">결과 없음</div>
                ) : (
                  <div className="overflow-x-auto rounded-xl border border-gray-700">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-gray-800 text-gray-400 text-left">
                          {queryResult.fields.map((f) => (
                            <th key={f} className="px-3 py-2 font-medium whitespace-nowrap">{f}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {queryResult.rows.map((row, i) => (
                          <tr key={i} className={`border-t border-gray-700/60 ${i % 2 === 0 ? "bg-gray-900" : "bg-gray-900/50"}`}>
                            {queryResult.fields.map((f) => {
                              const val     = row[f];
                              const isNull  = val === null || val === undefined;
                              const display = isNull ? "NULL"
                                : typeof val === "object" ? JSON.stringify(val)
                                : String(val);
                              return (
                                <td
                                  key={f}
                                  title={display}
                                  className={`px-3 py-2 max-w-xs truncate ${isNull ? "text-gray-600 italic" : "text-gray-200"}`}
                                >
                                  {display}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

          </div>
        )}

      </div>
    </main>
  );
}
