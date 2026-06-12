// U2 폴백용 결정적 mock — BACKEND_URL 미설정 시 BFF가 사용 (U2 §6 "canned 응답" 독립 빌드).

import { mockPaperPool } from "./mock-data";
import type {
  SummaryRequestBody,
  SummaryResponse,
  TranslationRequestBody,
  TranslationResult,
  VocabExplanation,
} from "./types";

const MOCK_GLOSSARY: Record<string, string> = {
  transformer: "트랜스포머",
  attention: "어텐션(주의 기제)",
  embedding: "임베딩",
  retrieval: "검색(리트리벌)",
};

function hitsFor(text: string): VocabExplanation[] {
  const lower = text.toLowerCase();
  return Object.entries(MOCK_GLOSSARY)
    .filter(([term]) => lower.includes(term))
    .map(([term, ko]) => ({ term, ko, note: "" }));
}

export function buildMockSummary(body: SummaryRequestBody): SummaryResponse {
  const seed = mockPaperPool().find((p) => p.id === body.paper_id);
  const title = seed?.title ?? `논문 ${body.paper_id}`;
  const abstract =
    `This paper studies ${title.toLowerCase()}. ` +
    "We propose a transformer-based method with attention and retrieval. " +
    "Experiments show consistent improvements over strong baselines.";
  const pro = body.mode === "pro";
  return {
    summary: {
      paper_id: body.paper_id,
      mode: body.mode,
      sections: pro
        ? {
            question: `본 논문은 "${title}" 주제에서 기존 접근의 한계를 규명한다 (mock).`,
            method: "transformer(트랜스포머) 기반 attention(어텐션) 구조를 제안한다.",
            result: "벤치마크에서 베이스라인 대비 일관된 성능 향상을 보고한다.",
            limit: "본 출력은 결정적 mock으로 실제 모델 추론을 대체하지 않는다.",
          }
        : {
            question: `이 논문이 풀려는 문제를 쉽게 말하면 "${title}"에 대한 거예요 (mock).`,
            method: "문장을 숫자로 바꿔 비교하는 방법을 써요. 약어 풀이: RAG(검색 증강 생성).",
            result: "기존 방법보다 좋아졌다는 결과를 보여 줘요.",
            limit: "이 답변은 시연용 가짜 응답이라 실제 모델의 답과 달라요.",
          },
      vocab_explanations: hitsFor(abstract),
      cost: { tokens_in: 512, tokens_out: 128 },
    },
    readability:
      body.mode === "undergrad"
        ? {
            mode: "undergrad",
            passed: true,
            metrics: {
              sentence_count: 4,
              average_eojeol_per_sentence: 12.5,
              max_eojeol_per_sentence: 18,
              difficult_token_count: 0,
            },
            issues: [],
          }
        : null,
    paper: { title, abstract },
  };
}

export function buildMockTranslation(body: TranslationRequestBody): TranslationResult {
  return {
    source_excerpt: body.source_excerpt,
    target_text: `(모의 번역) 선택하신 문장의 한국어 번역입니다: ${body.source_excerpt.slice(0, 80)} — 핵심 용어는 사전 표기를 따릅니다.`,
    glossary_hits: hitsFor(body.source_excerpt),
  };
}
