// U4 폴백용 결정적 mock — BACKEND_URL 미설정 시 BFF가 사용 (U4 §6 "fixture mock" 독립 빌드).
// 백엔드 FixtureCitation과 같은 방식: 중심 ID 해시로 시드 풀에서 결정적 선택.

import { mockPaperPool, type SeedPaper } from "./mock-data";
import type {
  CitationPaper,
  CitationRequestBody,
  CitationResponse,
  CitationRenderMode,
} from "./types";

const OUTGOING_N = 3;
const INCOMING_N = 5;
const BREAKPOINT_PX = 768; // 백엔드 FormFactorRouter와 동일 (NFR-MOBILE-05)

function stableHash(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = (h * 31 + value.charCodeAt(i)) >>> 0;
  }
  return h;
}

function toCitationPaper(seed: SeedPaper): CitationPaper {
  return {
    id: seed.id,
    title: seed.title,
    authors: seed.authors,
    year: seed.year,
    citations: seed.citations,
    similarity: 0,
    field_tags: seed.field_tags,
    abstract_len: 0,
  };
}

function pick(centerId: string, salt: string, n: number): CitationPaper[] {
  const pool = mockPaperPool();
  const picks: CitationPaper[] = [];
  for (let i = 0; i < n; i += 1) {
    const idx = stableHash(`${salt}:${centerId}:${i}`) % pool.length;
    const candidate = pool[idx];
    if (candidate.id !== centerId && !picks.some((p) => p.id === candidate.id)) {
      picks.push(toCitationPaper(candidate));
    }
  }
  return picks;
}

export function buildMockCitations(body: CitationRequestBody): CitationResponse {
  const render: CitationRenderMode =
    body.viewport_width < BREAKPOINT_PX || body.persona === "undergrad"
      ? "list"
      : "graph";
  const outgoing = pick(body.paper.id, "out", OUTGOING_N);
  const incoming = pick(body.paper.id, "in", INCOMING_N);
  return {
    view: {
      center: { ...body.paper, field_tags: [], abstract_len: 0 },
      outgoing,
      incoming,
      render,
      max_nodes: 30,
    },
    top_influence: [...incoming]
      .sort((a, b) => b.citations - a.citations)
      .slice(0, 3),
  };
}
