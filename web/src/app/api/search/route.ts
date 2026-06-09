import { NextRequest, NextResponse } from "next/server";
import { fetchArxiv } from "@/lib/apis/arxiv";
import { fetchSemanticScholar } from "@/lib/apis/semanticScholar";
import { fetchOpenAlex } from "@/lib/apis/openAlex";
import { upsertPapers } from "@/lib/upsertPapers";
import pool from "@/lib/db";
import type { NormalizedPaper } from "@/lib/apis/types";

const PER_SOURCE = 10; // 소스당 최대 결과 수

/** arxiv_id → s2_paper_id → openalex_id → doi → title 순으로 중복 제거 */
function deduplicateByKey(papers: NormalizedPaper[]): NormalizedPaper[] {
  const seen = new Set<string>();
  const result: NormalizedPaper[] = [];

  for (const p of papers) {
    const key =
      p.arxiv_id ??
      p.s2_paper_id ??
      p.openalex_id ??
      p.doi ??
      p.title.toLowerCase().slice(0, 80);

    if (!seen.has(key)) {
      seen.add(key);
      result.push(p);
    }
  }
  return result;
}

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim();
  if (!q) {
    return NextResponse.json({ error: "q is required" }, { status: 400 });
  }

  // ── 1. 외부 API 병렬 호출 ────────────────────────────────────────────
  const [arxivResult, s2Result, openAlexResult] = await Promise.allSettled([
    fetchArxiv(q, PER_SOURCE),
    fetchSemanticScholar(q, PER_SOURCE),
    fetchOpenAlex(q, PER_SOURCE),
  ]);

  const merged: NormalizedPaper[] = [];

  if (arxivResult.status === "fulfilled") merged.push(...arxivResult.value);
  else console.error("[search] arXiv error:", arxivResult.reason);

  if (s2Result.status === "fulfilled") merged.push(...s2Result.value);
  else console.error("[search] Semantic Scholar error:", s2Result.reason);

  if (openAlexResult.status === "fulfilled") merged.push(...openAlexResult.value);
  else console.error("[search] OpenAlex error:", openAlexResult.reason);

  // ── 2. 중복 제거 & DB upsert ─────────────────────────────────────────
  const unique = deduplicateByKey(merged);
  await upsertPapers(unique);

  // ── 3. DB에서 upsert된 논문 조회 (인용수 내림차순) ─────────────────────
  const arxivIds = unique.map((p) => p.arxiv_id).filter(Boolean);
  const s2Ids = unique.map((p) => p.s2_paper_id).filter(Boolean);
  const openAlexIds = unique.map((p) => p.openalex_id).filter(Boolean);

  const dbResult = await pool.query(
    `SELECT id, arxiv_id, s2_paper_id, openalex_id, doi,
            title, authors, year, abstract,
            pdf_object_key, citation_count, influential_count
       FROM papers
      WHERE status = 'active'
        AND (
          arxiv_id    = ANY($1::text[])
          OR s2_paper_id  = ANY($2::text[])
          OR openalex_id  = ANY($3::text[])
        )
      ORDER BY citation_count DESC`,
    [arxivIds, s2Ids, openAlexIds]
  );

  // DB에 없는 논문은 외부 API 결과로 폴백 (pdf_url 포함)
  const dbIds = new Set([
    ...dbResult.rows.map((r) => r.arxiv_id),
    ...dbResult.rows.map((r) => r.s2_paper_id),
    ...dbResult.rows.map((r) => r.openalex_id),
  ]);

  const fallback = unique
    .filter(
      (p) =>
        !dbIds.has(p.arxiv_id) &&
        !dbIds.has(p.s2_paper_id) &&
        !dbIds.has(p.openalex_id)
    )
    .map((p) => ({ ...p, id: null }));

  return NextResponse.json({
    query: q,
    sources: {
      arxiv: arxivResult.status === "fulfilled",
      semanticScholar: s2Result.status === "fulfilled",
      openAlex: openAlexResult.status === "fulfilled",
    },
    total: dbResult.rows.length + fallback.length,
    data: [...dbResult.rows, ...fallback],
  });
}
