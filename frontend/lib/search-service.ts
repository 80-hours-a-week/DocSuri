// 서버측 검색 — BACKEND_URL 프록시 또는 내장 mock.
// BFF route handler와 서버 컴포넌트(page) 초기 렌더가 공유한다. (클라이언트에서 import 금지)
//
// 폴백 정책: **네트워크 도달 불가(fetch throw)만** mock으로 폴백한다. 백엔드가 도달 가능한데
// 4xx/5xx를 반환하면 UpstreamError로 표면화 — 라이브 데모 중 백엔드 오류가 mock 200으로
// 가려지지 않게 한다.

import { buildMockResponse } from "./mock-data";
import type { SearchRequestBody, SearchResponse } from "./types";

export class UpstreamError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`upstream ${status}`);
    this.name = "UpstreamError";
  }
}

export async function performSearch(body: SearchRequestBody): Promise<SearchResponse> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return buildMockResponse(body); // 백엔드 미설정 → 단독 mock
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${backendUrl}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return buildMockResponse(body); // 도달 불가 → mock 폴백(단독 데모 지속)
  }

  if (!upstream.ok) {
    // 도달은 했으나 오류 — 가리지 않고 표면화.
    throw new UpstreamError(upstream.status, await upstream.text().catch(() => ""));
  }
  return (await upstream.json()) as SearchResponse;
}
