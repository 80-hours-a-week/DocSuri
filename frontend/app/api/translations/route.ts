// BFF — /api/translations (검증 후 performTranslation 위임).

import { NextResponse } from "next/server";

import { performTranslation } from "@/lib/comprehend-service";
import { UpstreamError } from "@/lib/search-service";
import type { TranslationRequestBody } from "@/lib/types";

const MAX_EXCERPT_LEN = 2000; // 백엔드 u2/api.py와 동일 상한

function normalizeBody(raw: unknown): TranslationRequestBody | null {
  if (typeof raw !== "object" || raw === null) return null;
  const body = raw as Record<string, unknown>;
  const excerpt =
    typeof body.source_excerpt === "string" ? body.source_excerpt.trim() : "";
  if (!excerpt || excerpt.length > MAX_EXCERPT_LEN) return null;
  return {
    source_excerpt: excerpt,
    input_mode: body.input_mode === "mobile" ? "mobile" : "desktop",
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
      { detail: "번역할 텍스트가 비어 있거나 너무 깁니다." },
      { status: 400 },
    );
  }
  try {
    return NextResponse.json(await performTranslation(body));
  } catch (err) {
    if (err instanceof UpstreamError) {
      return NextResponse.json(
        { detail: "번역에 실패했습니다." },
        { status: err.status },
      );
    }
    throw err;
  }
}
