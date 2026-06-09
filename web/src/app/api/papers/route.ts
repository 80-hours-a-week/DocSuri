import { NextRequest, NextResponse } from "next/server";
import pool from "@/lib/db";

const MAX_LIMIT = 50;

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;

  const q = searchParams.get("q")?.trim() ?? "";
  const sort = searchParams.get("sort") === "recent" ? "recent" : "citation";
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10));
  const limit = Math.min(
    MAX_LIMIT,
    Math.max(1, parseInt(searchParams.get("limit") ?? "20", 10))
  );
  const userId = searchParams.get("userId")?.trim() ?? "";
  const offset = (page - 1) * limit;

  try {
    // ── 1. 유저 라이브러리가 있는 경우: 벡터 유사도 추천 ──────────────────
    if (userId) {
      const libraryResult = await pool.query(
        `SELECT p.embedding
           FROM user_library ul
           JOIN papers p ON p.id = ul.paper_id
          WHERE ul.user_id = $1
            AND p.embedding IS NOT NULL`,
        [userId]
      );

      if (libraryResult.rowCount && libraryResult.rowCount > 0) {
        // 라이브러리 논문 임베딩의 평균 벡터 계산 (pgvector AVG 지원)
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
          // $1: avgVec, $2: userId, $3: limit, $4: offset, [$5: keyword]
          const baseParams: unknown[] = [avgVec, userId, limit, offset];
          const keywordFilter = q
            ? `AND (p.title ILIKE $5 OR p.abstract ILIKE $5)`
            : "";
          if (q) baseParams.push(`%${q}%`);

          const result = await pool.query(
            `SELECT p.id, p.arxiv_id, p.s2_paper_id, p.openalex_id, p.doi,
                    p.title, p.authors, p.year, p.abstract, p.pdf_object_key,
                    p.citation_count, p.influential_count,
                    1 - (p.embedding <=> $1::vector) AS similarity_score
               FROM papers p
              WHERE p.status = 'active'
                AND p.id NOT IN (
                  SELECT paper_id FROM user_library WHERE user_id = $2
                )
                ${keywordFilter}
              ORDER BY p.embedding <=> $1::vector
              LIMIT $3 OFFSET $4`,
            baseParams
          );

          return NextResponse.json({
            mode: "vector",
            page,
            limit,
            data: result.rows,
          });
        }
      }
    }

    // ── 2. 폴백: 인용수 / 최신순 정렬 ────────────────────────────────────
    const orderBy =
      sort === "recent"
        ? "p.year DESC NULLS LAST, p.citation_count DESC"
        : "p.citation_count DESC, p.year DESC NULLS LAST";

    const params: (string | number)[] = [limit, offset];
    const keywordFilter = q
      ? `AND (p.title ILIKE $3 OR p.abstract ILIKE $3)`
      : "";
    if (q) params.push(`%${q}%`);

    const [dataResult, countResult] = await Promise.all([
      pool.query(
        `SELECT p.id, p.arxiv_id, p.s2_paper_id, p.openalex_id, p.doi,
                p.title, p.authors, p.year, p.abstract, p.pdf_object_key,
                p.citation_count, p.influential_count
           FROM papers p
          WHERE p.status = 'active'
            ${keywordFilter}
          ORDER BY ${orderBy}
          LIMIT $1 OFFSET $2`,
        params
      ),
      pool.query(
        `SELECT COUNT(*) AS total
           FROM papers p
          WHERE p.status = 'active'
            ${keywordFilter}`,
        q ? [`%${q}%`] : []
      ),
    ]);

    return NextResponse.json({
      mode: "fallback",
      sort,
      page,
      limit,
      total: parseInt(countResult.rows[0].total, 10),
      data: dataResult.rows,
    });
  } catch (err) {
    console.error("[GET /api/papers]", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
