// 폴백용 결정적 mock — BACKEND_URL 미설정 시 BFF가 사용한다 (U1 §6 "독립 빌드").
// 백엔드 도메인 로직(필터·정렬·한국어 매핑·확장)을 *가볍게* 재현해 UI가 단독으로 동작하게 한다.
// 실제 임베딩 품질은 가짜다 — similarity는 합성값.

import type {
  DifficultyLabel,
  ExpandedTerm,
  QueryMapping,
  SearchRequestBody,
  SearchResponse,
  SearchResultPaper,
} from "./types";

export interface SeedPaper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  citations: number;
  field_tags: string[];
  difficulty: DifficultyLabel;
}

// U4 mock-citations가 같은 시드 풀을 공유한다 (mock 간 ID 정합).
export function mockPaperPool(): SeedPaper[] {
  return SEED;
}

// ~24편 시드 (난이도·연도·분야 혼합). 백엔드 corpus_seed.json의 대역.
const SEED: SeedPaper[] = [
  { id: "2606.11190", title: "Attention Is All You Need: A Gentle Introduction", authors: ["A. Vaswani", "N. Shazeer"], year: 2024, citations: 488, field_tags: ["cs.LG", "cs.CL"], difficulty: "입문" },
  { id: "2606.11189", title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP", authors: ["P. Lewis", "E. Perez"], year: 2025, citations: 474, field_tags: ["cs.CL"], difficulty: "입문" },
  { id: "2606.11188", title: "A Survey of Transformer-Based Summarization", authors: ["J. Kim", "S. Lee"], year: 2025, citations: 312, field_tags: ["cs.CL"], difficulty: "입문" },
  { id: "2606.11187", title: "Vision Transformers for Image Recognition at Scale", authors: ["A. Dosovitskiy"], year: 2024, citations: 401, field_tags: ["cs.CV"], difficulty: "중급" },
  { id: "2606.11186", title: "Scaling Laws for Neural Language Models", authors: ["J. Kaplan", "S. McCandlish"], year: 2023, citations: 388, field_tags: ["cs.LG"], difficulty: "중급" },
  { id: "2606.11185", title: "Efficient Fine-Tuning via Low-Rank Adaptation", authors: ["E. Hu", "Y. Shen"], year: 2025, citations: 356, field_tags: ["cs.LG", "cs.CL"], difficulty: "중급" },
  { id: "2606.11184", title: "Dense Passage Retrieval for Open-Domain QA", authors: ["V. Karpukhin"], year: 2024, citations: 290, field_tags: ["cs.CL", "cs.IR"], difficulty: "중급" },
  { id: "2606.11183", title: "Contrastive Language-Image Pretraining", authors: ["A. Radford"], year: 2024, citations: 333, field_tags: ["cs.CV", "cs.LG"], difficulty: "중급" },
  { id: "2606.11182", title: "Chain-of-Thought Prompting Elicits Reasoning", authors: ["J. Wei"], year: 2025, citations: 275, field_tags: ["cs.CL"], difficulty: "입문" },
  { id: "2606.11181", title: "Sparse Mixture-of-Experts for Scalable Transformers", authors: ["N. Shazeer"], year: 2026, citations: 142, field_tags: ["cs.LG"], difficulty: "고급" },
  { id: "2606.11180", title: "Diffusion Models Beat GANs on Image Synthesis", authors: ["P. Dhariwal", "A. Nichol"], year: 2023, citations: 360, field_tags: ["cs.CV"], difficulty: "중급" },
  { id: "2606.11179", title: "Theoretical Limits of In-Context Learning", authors: ["S. Garg"], year: 2026, citations: 88, field_tags: ["cs.LG", "math.ST", "stat.ML"], difficulty: "고급" },
  { id: "2606.11178", title: "Instruction Tuning with Human Feedback", authors: ["L. Ouyang"], year: 2025, citations: 298, field_tags: ["cs.CL"], difficulty: "입문" },
  { id: "2606.11177", title: "Graph Neural Networks: A Review of Methods", authors: ["J. Zhou"], year: 2024, citations: 254, field_tags: ["cs.LG"], difficulty: "중급" },
  { id: "2606.11176", title: "Self-Supervised Speech Representation Learning", authors: ["A. Baevski"], year: 2024, citations: 201, field_tags: ["eess.AS", "cs.CL"], difficulty: "고급" },
  { id: "2606.11175", title: "A Beginner's Guide to Word Embeddings", authors: ["T. Mikolov"], year: 2023, citations: 420, field_tags: ["cs.CL"], difficulty: "입문" },
  { id: "2606.11174", title: "Adversarial Robustness of Deep Classifiers", authors: ["A. Madry"], year: 2025, citations: 176, field_tags: ["cs.LG", "cs.CR"], difficulty: "고급" },
  { id: "2606.11173", title: "Long-Context Transformers with Linear Attention", authors: ["A. Katharopoulos"], year: 2026, citations: 120, field_tags: ["cs.LG", "cs.CL"], difficulty: "고급" },
  { id: "2606.11172", title: "Parameter-Efficient Transfer Learning Survey", authors: ["N. Houlsby"], year: 2025, citations: 233, field_tags: ["cs.LG"], difficulty: "중급" },
  { id: "2606.11171", title: "Neural Machine Translation by Jointly Learning to Align", authors: ["D. Bahdanau"], year: 2023, citations: 455, field_tags: ["cs.CL"], difficulty: "입문" },
  { id: "2606.11170", title: "Multimodal Foundation Models: A Phase Diagram", authors: ["I. Kamai", "R. Balestriero"], year: 2026, citations: 95, field_tags: ["cs.LG", "cs.CV"], difficulty: "고급" },
  { id: "2606.11169", title: "Knowledge Distillation for Compact Language Models", authors: ["V. Sanh"], year: 2024, citations: 267, field_tags: ["cs.CL", "cs.LG"], difficulty: "중급" },
  { id: "2606.11168", title: "Evaluating Factual Consistency in Summarization", authors: ["W. Kryscinski"], year: 2025, citations: 188, field_tags: ["cs.CL"], difficulty: "중급" },
  { id: "2606.11167", title: "An Introduction to Reinforcement Learning from Human Feedback", authors: ["N. Stiennon"], year: 2024, citations: 305, field_tags: ["cs.LG", "cs.CL"], difficulty: "입문" },
];

const DIFFICULTY_RANK: Record<DifficultyLabel, number> = { 입문: 0, 중급: 1, 고급: 2 };

const EXPANSION_SEED: Record<string, string[]> = {
  rag: ["retrieval-augmented generation", "retrieval augmented"],
  llm: ["large language model"],
  nlp: ["natural language processing"],
  cv: ["computer vision"],
  rl: ["reinforcement learning"],
  transformer: ["self-attention", "attention mechanism"],
  attention: ["self-attention"],
  summarization: ["abstractive summarization", "text summarization"],
};

const KO_EN_SEED: Record<string, string> = {
  트랜스포머: "transformer",
  어텐션: "attention",
  검색: "retrieval",
  생성: "generation",
  요약: "summarization",
  번역: "translation",
  신경망: "neural network",
  언어모델: "language model",
  강화학습: "reinforcement learning",
};

function isKorean(text: string): boolean {
  return /[가-힣]/.test(text);
}

function expandedTermsFor(query: string, selected: string[]): ExpandedTerm[] {
  const out: string[] = [];
  for (const token of query.toLowerCase().split(/[^a-z0-9가-힣]+/).filter(Boolean)) {
    for (const exp of EXPANSION_SEED[token] ?? []) {
      if (!out.includes(exp)) out.push(exp);
    }
  }
  return out.slice(0, 8).map((term) => ({ term, checked: selected.includes(term) }));
}

function mappingFor(query: string): QueryMapping {
  const keywords: string[] = [];
  for (const [ko, en] of Object.entries(KO_EN_SEED)) {
    if (query.includes(ko) && !keywords.includes(en)) keywords.push(en);
  }
  if (keywords.length === 0) keywords.push(query.trim());
  return {
    en_keywords: keywords,
    explanation: `입력하신 "${query.trim()}"을(를) 영문 키워드 ${keywords.join(", ")}(으)로 매핑해 검색했습니다.`,
  };
}

// 백엔드 search_for의 경량 재현: 필터 → 정렬 → 상위 20 + 확장/매핑.
export function buildMockResponse(req: SearchRequestBody): SearchResponse {
  const lang = isKorean(req.query) ? "ko" : "en";
  const { year_min, year_max, field_tags } = req.filters;

  const rows = SEED.filter((p) => {
    if (year_min != null && p.year < year_min) return false;
    if (year_max != null && p.year > year_max) return false;
    if (field_tags.length && !field_tags.some((t) => p.field_tags.includes(t))) return false;
    return true;
  });

  // 합성 유사도: 시드 순서를 기본 유사도로(상위일수록 높음).
  const withSim = rows.map((p, i) => ({
    paper: p,
    similarity: Number((0.52 - i * 0.012).toFixed(4)),
  }));

  if (req.sort_key === "citations") {
    withSim.sort((a, b) => b.paper.citations - a.paper.citations);
  } else if (req.sort_key === "recency") {
    withSim.sort((a, b) => b.paper.year - a.paper.year);
  } else if (lang === "ko") {
    // 한국어: 난이도 입문 우선(오름차순) → 유사도 내림차순
    withSim.sort(
      (a, b) =>
        DIFFICULTY_RANK[a.paper.difficulty] - DIFFICULTY_RANK[b.paper.difficulty] ||
        b.similarity - a.similarity,
    );
  } else {
    withSim.sort((a, b) => b.similarity - a.similarity);
  }

  const papers: SearchResultPaper[] = withSim.slice(0, 20).map(({ paper, similarity }) => ({
    id: paper.id,
    title: paper.title,
    authors: paper.authors,
    year: paper.year,
    citations: paper.citations,
    similarity,
    difficulty: paper.difficulty,
  }));

  return {
    result: {
      query: req.query,
      expanded_terms: expandedTermsFor(req.query, req.selected_terms),
      papers,
      filters: req.filters,
      lang,
    },
    query_mapping: lang === "ko" ? mappingFor(req.query) : null,
  };
}
