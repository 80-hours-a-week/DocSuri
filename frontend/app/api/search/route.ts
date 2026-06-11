// BFF — /api/search. 입력 검증(빈/과길이 쿼리) 후 performSearch(프록시↔mock)에 위임.
// 클라이언트는 항상 이 엔드포인트만 호출한다(CORS 불필요).

import { NextResponse } from "next/server";

import { performSearch, UpstreamError } from "@/lib/search-service";
import type { SearchRequestBody } from "@/lib/types";

const MAX_QUERY_LEN = 500;
const MAX_SELECTED_TERMS = 20;

function normalizeBody(raw: unknown): SearchRequestBody | null {
  if (typeof raw !== "object" || raw === null) return null;
  const body = raw as Record<string, unknown>;
  const query = typeof body.query === "string" ? body.query.trim() : "";
  if (!query || query.length > MAX_QUERY_LEN) return null;

  const f = (body.filters ?? {}) as Record<string, unknown>;
  const sort = body.sort_key;
  return {
    query,
    filters: {
      year_min: typeof f.year_min === "number" ? f.year_min : null,
      year_max: typeof f.year_max === "number" ? f.year_max : null,
      field_tags: Array.isArray(f.field_tags)
        ? f.field_tags.filter((t): t is string => typeof t === "string")
        : [],
    },
    sort_key: sort === "citations" || sort === "recency" ? sort : "similarity",
    selected_terms: Array.isArray(body.selected_terms)
      ? body.selected_terms.filter((t): t is string => typeof t === "string").slice(0, MAX_SELECTED_TERMS)
      : [],
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
    return NextResponse.json({ detail: "검색어가 비어 있거나 너무 깁니다." }, { status: 400 });
  }

  try {
    return NextResponse.json(await performSearch(body));
  } catch (err) {
    // 백엔드가 도달 가능하지만 오류 반환 → 상태를 그대로 전달(mock으로 가리지 않음).
    if (err instanceof UpstreamError) {
      return NextResponse.json(
        { detail: "백엔드 검색에 실패했습니다." },
        { status: err.status },
      );
    }
    throw err;
  }
}
