import { NextRequest, NextResponse } from "next/server";
import pool from "@/lib/db";

// GET /api/library?userId=xxx  → 유저 라이브러리 조회
export async function GET(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get("userId")?.trim();
  if (!userId) {
    return NextResponse.json({ error: "userId is required" }, { status: 400 });
  }

  const result = await pool.query(
    `SELECT p.id, p.arxiv_id, p.s2_paper_id, p.openalex_id, p.doi,
            p.title, p.authors, p.year, p.abstract,
            p.citation_count, p.influential_count,
            ul.added_at, ul.tags
       FROM user_library ul
       JOIN papers p ON p.id = ul.paper_id
      WHERE ul.user_id = $1
      ORDER BY ul.added_at DESC`,
    [userId]
  );

  return NextResponse.json({ data: result.rows });
}

// POST /api/library  body: { userId, paperId }  → 논문 추가
export async function POST(req: NextRequest) {
  let body: { userId?: string; paperId?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { userId, paperId } = body;
  if (!userId || !paperId) {
    return NextResponse.json(
      { error: "userId and paperId are required" },
      { status: 400 }
    );
  }

  await pool.query(
    `INSERT INTO user_library (user_id, paper_id)
     VALUES ($1, $2)
     ON CONFLICT (user_id, paper_id) DO NOTHING`,
    [userId, paperId]
  );

  return NextResponse.json({ ok: true });
}

// DELETE /api/library?userId=xxx&paperId=123  → 논문 제거
export async function DELETE(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get("userId")?.trim();
  const paperId = req.nextUrl.searchParams.get("paperId");

  if (!userId || !paperId) {
    return NextResponse.json(
      { error: "userId and paperId are required" },
      { status: 400 }
    );
  }

  await pool.query(
    `DELETE FROM user_library WHERE user_id = $1 AND paper_id = $2`,
    [userId, parseInt(paperId, 10)]
  );

  return NextResponse.json({ ok: true });
}
