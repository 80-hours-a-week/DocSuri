// 클라이언트 → BFF(/api/summaries·/api/translations) 호출 (lib/api.ts 패턴).

import type {
  Persona,
  SummaryResponse,
  TranslationRequestBody,
  TranslationResult,
} from "./types";

async function post<T>(path: string, body: unknown, failMessage: string): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${failMessage} (${res.status}) ${detail}`.trim());
  }
  return (await res.json()) as T;
}

export function fetchSummary(paperId: string, mode: Persona): Promise<SummaryResponse> {
  return post("/api/summaries", { paper_id: paperId, mode }, "요약 요청 실패");
}

export function fetchTranslation(
  excerpt: string,
  inputMode: TranslationRequestBody["input_mode"],
): Promise<TranslationResult> {
  return post(
    "/api/translations",
    { source_excerpt: excerpt, input_mode: inputMode },
    "번역 요청 실패",
  );
}
