// 서버측 요약·번역 — BACKEND_URL 프록시 또는 내장 mock (search-service 폴백 정책 동일).

import { buildMockSummary, buildMockTranslation } from "./mock-comprehend";
import { UpstreamError } from "./search-service";
import type {
  SummaryRequestBody,
  SummaryResponse,
  TranslationRequestBody,
  TranslationResult,
} from "./types";

async function proxyPost<T>(path: string, body: unknown, fallback: () => T): Promise<T> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return fallback();
  let upstream: Response;
  try {
    upstream = await fetch(`${backendUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return fallback(); // 도달 불가 → mock (단독 데모 지속)
  }
  if (!upstream.ok) {
    throw new UpstreamError(upstream.status, await upstream.text().catch(() => ""));
  }
  return (await upstream.json()) as T;
}

export function performSummary(body: SummaryRequestBody): Promise<SummaryResponse> {
  return proxyPost("/api/summaries", body, () => buildMockSummary(body));
}

export function performTranslation(
  body: TranslationRequestBody,
): Promise<TranslationResult> {
  return proxyPost("/api/translations", body, () => buildMockTranslation(body));
}
