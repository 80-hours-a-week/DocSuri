import { NextRequest, NextResponse } from "next/server";
import pool from "@/lib/db";

// SELECT / WITH 만 허용 (읽기 전용)
const ALLOWED = /^\s*(select|with)\s/i;

export async function POST(req: NextRequest) {
  let sql: string;
  try {
    const body = await req.json();
    sql = (body.sql ?? "").trim();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (!sql) {
    return NextResponse.json({ error: "SQL이 비어있습니다." }, { status: 400 });
  }

  if (!ALLOWED.test(sql)) {
    return NextResponse.json(
      { error: "SELECT / WITH 쿼리만 실행할 수 있습니다." },
      { status: 403 }
    );
  }

  const start = Date.now();
  try {
    const result = await pool.query(sql);
    return NextResponse.json({
      rows:    result.rows,
      fields:  result.fields.map((f) => f.name),
      rowCount: result.rowCount ?? 0,
      elapsed: Date.now() - start,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 400 });
  }
}
