import { NextRequest, NextResponse } from "next/server";
import pool from "@/lib/db";
import { embedText } from "@/lib/embed";
import { rankPapers, CandidatePaper, LibraryPaper } from "@/lib/llm";

const CANDIDATE_LIMIT = 30; // LLM에게 넘길 후보 수

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const userId = searchParams.get("userId")?.trim() ?? "";

  try {
    // ── 1. 유저 라이브러리 조회 ─────────────────────────────────────────
    let library: LibraryPaper[] = [];
    let libraryPaperIds: number[] = [];

    if (userId) {
      const libResult = await pool.query(
        `SELECT p.id, p.title, p.year, p.abstract, p.embedding
           FROM user_library ul
           JOIN papers p ON p.id = ul.paper_id
          WHERE ul.user_id = $1`,
        [userId]
      );
      library = libResult.rows.map((r) => ({
        title: r.title,
        year: r.year,
        abstract: r.abstract,
      }));
      libraryPaperIds = libResult.rows.map((r) => r.id as number);
    }

    // ── 2. 후보 논문 조회 ───────────────────────────────────────────────
    let candidates: CandidatePaper[] = [];

    const excludeClause =
      libraryPaperIds.length > 0
        ? `AND p.id NOT IN (${libraryPaperIds.map((_, i) => `$${i + 2}`).join(",")})`
        : "";

    if (library.length > 0) {
      // 라이브러리가 있으면: 라이브러리 평균 벡터로 유사도 기반 후보 추출
      const avgResult = await pool.query(
        `SELECT AVG(p.embedding)::vector AS avg_vec
           FROM user_library ul
           JOIN papers p ON p.id = ul.paper_id
          WHERE ul.user_id = $1
            AND p.embedding IS NOT NULL`,
        [userId]
      );

      const avgVec = avgResult.rows[0]?.avg_vec;

      if (avgVec) {
        const params: unknown[] = [avgVec, ...libraryPaperIds, CANDIDATE_LIMIT];
        const offsetIdx = params.length;
        params.push(0);

        const res = await pool.query(
          `SELECT p.id, p.title, p.year, p.abstract, p.citation_count,
                  1 - (p.embedding <=> $1::vector) AS similarity_score
             FROM papers p
            WHERE p.status = 'active'
              AND p.embedding IS NOT NULL
              ${excludeClause}
            ORDER BY p.embedding <=> $1::vector
            LIMIT $${offsetIdx} OFFSET $${offsetIdx + 1}`,
          params
        );
        candidates = res.rows.map((r) => ({
          id: r.id,
          title: r.title,
          year: r.year,
          abstract: r.abstract,
          citation_count: r.citation_count,
          similarity_score: parseFloat(r.similarity_score),
        }));
      }
    }

    // 벡터 후보가 없거나 라이브러리가 비었으면 인용수+최신순 상위 30건
    if (candidates.length === 0) {
      const params: unknown[] = [CANDIDATE_LIMIT, 0, ...libraryPaperIds];
      const res = await pool.query(
        `SELECT p.id, p.title, p.year, p.abstract, p.citation_count
           FROM papers p
          WHERE p.status = 'active'
            ${excludeClause}
          ORDER BY p.citation_count DESC, p.year DESC NULLS LAST
          LIMIT $1 OFFSET $2`,
        params
      );
      candidates = res.rows.map((r) => ({
        id: r.id,
        title: r.title,
        year: r.year,
        abstract: r.abstract,
        citation_count: r.citation_count,
      }));
    }

    if (candidates.length === 0) {
      return NextResponse.json({ mode: "empty", data: [] });
    }

    // ── 3. Bedrock Nova Micro로 추천 순위 결정 ──────────────────────────
    const { rankedIds, reason } = await rankPapers(library, candidates);

    // rankedIds 순서대로 candidates 재정렬 (LLM이 빠뜨린 항목은 뒤에 추가)
    const candidateMap = new Map(candidates.map((c) => [c.id, c]));
    const ranked = rankedIds
      .filter((id) => candidateMap.has(id))
      .map((id) => candidateMap.get(id)!);
    const missing = candidates.filter((c) => !rankedIds.includes(c.id));
    const orderedIds = [...ranked, ...missing].map((c) => c.id);

    // ── 4. DB에서 전체 컬럼 조회 (orderedIds 순서 유지) ─────────────────
    if (orderedIds.length === 0) {
      return NextResponse.json({ mode: "empty", data: [] });
    }

    const placeholders = orderedIds.map((_, i) => `$${i + 1}`).join(",");
    const orderExpr = orderedIds
      .map((id, i) => `WHEN $${i + 1} THEN ${i}`)
      .join(" ");

    const finalResult = await pool.query(
      `SELECT p.id, p.arxiv_id, p.s2_paper_id, p.openalex_id, p.doi,
              p.title, p.authors, p.year, p.abstract, p.pdf_object_key,
              p.citation_count, p.influential_count
         FROM papers p
        WHERE p.id IN (${placeholders})
        ORDER BY CASE p.id ${orderExpr} END`,
      orderedIds
    );

    const mode = library.length > 0 ? "ai-vector" : "ai-fallback";
    return NextResponse.json({
      mode,
      reason,
      data: finalResult.rows,
    });
  } catch (err) {
    console.error("[GET /api/recommend]", err);
    return NextResponse.json(
      { error: "추천 생성 실패", detail: String(err) },
      { status: 500 }
    );
  }
}
