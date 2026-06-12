// 클라이언트 → BFF(/api/citations) 호출 (lib/api.ts 패턴).

import type {
  CitationRequestBody,
  CitationResponse,
  Persona,
  SearchResultPaper,
} from "./types";

export async function fetchCitations(
  paper: SearchResultPaper,
  viewportWidth: number,
  persona?: Persona,
): Promise<CitationResponse> {
  const body: CitationRequestBody = {
    paper: {
      id: paper.id,
      title: paper.title,
      authors: paper.authors,
      year: paper.year,
      citations: paper.citations,
      similarity: paper.similarity,
    },
    viewport_width: viewportWidth,
    ...(persona ? { persona } : {}),
  };
  const res = await fetch("/api/citations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`인용 흐름 조회 실패 (${res.status}) ${detail}`.trim());
  }
  return (await res.json()) as CitationResponse;
}
