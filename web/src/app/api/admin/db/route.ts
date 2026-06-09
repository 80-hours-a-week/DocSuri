import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET() {
  const [papersResult, libraryResult] = await Promise.all([
    pool.query(`
      SELECT
        id, arxiv_id, s2_paper_id, openalex_id,
        LEFT(title, 80)            AS title,
        year,
        citation_count,
        CASE WHEN embedding IS NOT NULL THEN true ELSE false END AS has_embedding,
        status,
        TO_CHAR(created_at AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI:SS') AS created_at
      FROM papers
      ORDER BY id DESC
    `),
    pool.query(`
      SELECT
        ul.user_id,
        ul.paper_id,
        LEFT(p.title, 80)          AS paper_title,
        ul.tags,
        TO_CHAR(ul.added_at AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI:SS') AS added_at
      FROM user_library ul
      JOIN papers p ON p.id = ul.paper_id
      ORDER BY ul.added_at DESC
    `),
  ]);

  return NextResponse.json({
    papers:  papersResult.rows,
    library: libraryResult.rows,
    stats: {
      total:    papersResult.rowCount,
      embedded: papersResult.rows.filter((r) => r.has_embedding).length,
      library:  libraryResult.rowCount,
    },
  });
}
