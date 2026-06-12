// 서버측 인용 조회 — BACKEND_URL 프록시 또는 내장 mock (search-service.ts와 동일 폴백 정책:
// 네트워크 도달 불가만 mock 폴백, 도달 가능한 오류는 UpstreamError로 표면화).

import { buildMockCitations } from "./mock-citations";
import { UpstreamError } from "./search-service";
import type { CitationRequestBody, CitationResponse } from "./types";

export async function performCitations(
  body: CitationRequestBody,
): Promise<CitationResponse> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return buildMockCitations(body);
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${backendUrl}/api/citations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return buildMockCitations(body); // 도달 불가 → mock 폴백(단독 데모 지속)
  }

  if (!upstream.ok) {
    throw new UpstreamError(upstream.status, await upstream.text().catch(() => ""));
  }
  return (await upstream.json()) as CitationResponse;
}
