// BFF — /api/summaries (검증 후 performSummary 위임 — /api/search route 패턴).

import { NextResponse } from "next/server";

import { performSummary } from "@/lib/comprehend-service";
import { UpstreamError } from "@/lib/search-service";
import type { Persona, SummaryRequestBody } from "@/lib/types";

const ARXIV_ID = /^\d{4}\.\d{4,5}(v\d+)?$/;

function normalizeBody(raw: unknown): SummaryRequestBody | null {
  if (typeof raw !== "object" || raw === null) return null;
  const body = raw as Record<string, unknown>;
  const paperId = typeof body.paper_id === "string" ? body.paper_id.trim() : "";
  if (!ARXIV_ID.test(paperId)) return null;
  const mode: Persona = body.mode === "undergrad" ? "undergrad" : "pro";
  return { paper_id: paperId, mode };
}

export async function POST(request: Request) {
  let parsed: unknown;
  try {
    parsed = await request.json();
  } catch {
    return NextResponse.json({ detail: "잘못된 요청 본문입니다." }, { status: 400 });
  }
  const body = normalizeBody(parsed);
  if (!body) {
    return NextResponse.json({ detail: "paper_id가 올바르지 않습니다." }, { status: 400 });
  }
  try {
    return NextResponse.json(await performSummary(body));
  } catch (err) {
    if (err instanceof UpstreamError) {
      return NextResponse.json(
        { detail: "요약 생성에 실패했습니다." },
        { status: err.status },
      );
    }
    throw err;
  }
}
