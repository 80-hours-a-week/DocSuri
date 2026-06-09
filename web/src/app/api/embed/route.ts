import { NextRequest, NextResponse } from "next/server";
import pool from "@/lib/db";
import { embedBatch } from "@/lib/embed";

const BATCH_SIZE = 20; // 한 번에 처리할 논문 수

/**
 * POST /api/embed
 * DB에서 embedding이 없는 논문을 가져와 Bedrock Titan으로 임베딩 후 저장.
 * body: { limit?: number }  — 기본 BATCH_SIZE
 */
export async function POST(req: NextRequest) {
  let limit = BATCH_SIZE;
  try {
    const body = await req.json();
    if (typeof body.limit === "number") limit = Math.min(body.limit, 100);
  } catch {
    // body 없으면 기본값 사용
  }

  // embedding이 없고 abstract가 있는 논문 우선
  const { rows } = await pool.query(
    `SELECT id, title, abstract
       FROM papers
      WHERE status = 'active'
        AND embedding IS NULL
      ORDER BY (abstract IS NOT NULL) DESC, id
      LIMIT $1`,
    [limit]
  );

  if (rows.length === 0) {
    return NextResponse.json({ message: "임베딩할 논문이 없습니다.", processed: 0 });
  }

  // 임베딩할 텍스트 구성: "제목. 요약" 또는 "제목"만
  const texts = rows.map((r: { title: string; abstract: string | null }) =>
    r.abstract ? `${r.title}. ${r.abstract}` : r.title
  );

  const embeddings = await embedBatch(texts);

  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < rows.length; i++) {
    const vec = embeddings[i];
    if (!vec) {
      failCount++;
      continue;
    }

    await pool.query(
      `UPDATE papers SET embedding = $1 WHERE id = $2`,
      [`[${vec.join(",")}]`, rows[i].id]
    );
    successCount++;
  }

  return NextResponse.json({
    processed: rows.length,
    success: successCount,
    failed: failCount,
  });
}

/**
 * GET /api/embed
 * 임베딩 대기 중인 논문 수 확인용
 */
export async function GET() {
  const { rows } = await pool.query(
    `SELECT
       COUNT(*) FILTER (WHERE embedding IS NULL) AS pending,
       COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
       COUNT(*) AS total
     FROM papers
     WHERE status = 'active'`
  );

  return NextResponse.json(rows[0]);
}
