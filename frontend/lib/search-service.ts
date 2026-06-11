// 서버측 검색 — BACKEND_URL 프록시(실패 시 mock 폴백) 또는 내장 mock.
// BFF route handler와 서버 컴포넌트(page) 초기 렌더가 공유한다. (클라이언트에서 import 금지)

import { buildMockResponse } from "./mock-data";
import type { SearchRequestBody, SearchResponse } from "./types";

export async function performSearch(body: SearchRequestBody): Promise<SearchResponse> {
  const backendUrl = process.env.BACKEND_URL;
  if (backendUrl) {
    try {
      const upstream = await fetch(`${backendUrl}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
      });
      if (upstream.ok) {
        return (await upstream.json()) as SearchResponse;
      }
      // 4xx/5xx는 프록시 경로(route handler)에서 별도 처리. 여기선 폴백.
    } catch {
      // 백엔드 도달 불가 → mock 폴백 (단독 데모 지속)
    }
  }
  return buildMockResponse(body);
}
