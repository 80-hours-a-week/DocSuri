// BFF — /api/citations. 입력 검증 후 performCitations(프록시↔mock)에 위임.
// /api/search route와 동일 구조 — 클라이언트는 항상 BFF만 호출한다.

import { NextResponse } from "next/server";

import { performCitations } from "@/lib/citation-service";
import { UpstreamError } from "@/lib/search-service";
import type { CitationRequestBody, Persona } from "@/lib/types";

const MAX_ID_LEN = 64;
const MAX_TITLE_LEN = 500;

function normalizeBody(raw: unknown): CitationRequestBody | null {
  if (typeof raw !== "object" || raw === null) return null;
  const body = raw as Record<string, unknown>;

  const p = (body.paper ?? {}) as Record<string, unknown>;
  const id = typeof p.id === "string" ? p.id.trim() : "";
  const title = typeof p.title === "string" ? p.title.trim() : "";
  if (!id || id.length > MAX_ID_LEN || !title || title.length > MAX_TITLE_LEN) {
    return null;
  }

  const viewport = body.viewport_width;
  const persona = body.persona;
  return {
    paper: {
      id,
      title,
      authors: Array.isArray(p.authors)
        ? p.authors.filter((a): a is string => typeof a === "string").slice(0, 20)
        : [],
      year: typeof p.year === "number" ? p.year : 0,
      citations: typeof p.citations === "number" ? p.citations : 0,
      similarity: typeof p.similarity === "number" ? p.similarity : 0,
    },
    viewport_width:
      typeof viewport === "number" && viewport >= 240 && viewport <= 10_000
        ? Math.round(viewport)
        : 1280,
    ...(persona === "pro" || persona === "undergrad"
      ? { persona: persona as Persona }
      : {}),
  };
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
    return NextResponse.json(
      { detail: "중심 논문 정보가 비어 있거나 잘못되었습니다." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await performCitations(body));
  } catch (err) {
    if (err instanceof UpstreamError) {
      return NextResponse.json(
        { detail: "인용 정보 조회에 실패했습니다." },
        { status: err.status },
      );
    }
    throw err;
  }
}
