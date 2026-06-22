// Dev-only summarize/translate/full-text fixtures (mock transport layer, same as
// searchFixtures). Production is real-first (real BFF) — these are never shipped;
// they let the U7 surface be previewed in dev (NEXT_PUBLIC_DOCSURI_REAL_API unset).
import type { SummaryOkDTO, TranslationOkDTO, FullTextOkDTO } from '@/types/generated';
import type { GlossaryUpsertResultDTO, GlossaryTermDTO } from '@/types/glossary';

export const summaryResponse: SummaryOkDTO = {
  status: 'ok',
  task: 'summary',
  meta: { source: 'full_text' },
  cached: false,
  summary: {
    tldr: 'RNN·CNN 없이 어텐션만으로 시퀀스 변환을 수행하는 Transformer를 제안한다. 병렬화가 쉬워 학습이 빠르고 번역 품질도 최고 수준이다.',
    contributions: [
      '순환·합성곱 구조를 제거하고 셀프 어텐션만으로 인코더-디코더를 구성',
      '멀티헤드 어텐션으로 서로 다른 표현 부분공간을 동시에 학습',
      'WMT 2014 영-독/영-불 번역에서 당시 SOTA 달성',
    ],
    method:
      '인코더와 디코더를 각각 6개 층으로 쌓고, 각 층은 멀티헤드 셀프 어텐션과 위치별 피드포워드 네트워크로 구성한다. 순서 정보는 사인·코사인 위치 인코딩으로 주입한다.',
    results:
      '영-독 28.4 BLEU, 영-불 41.8 BLEU로 기존 최고 모델을 능가하면서 학습 비용은 크게 줄였다(8 GPU로 3.5일).',
    limitations:
      '입력 길이에 대해 어텐션이 제곱 복잡도를 가져 매우 긴 시퀀스에는 비용이 크다. 위치 인코딩의 외삽 한계도 존재한다.',
    reproducibility: {
      code: '공개 — tensor2tensor 저장소에 구현 제공',
      data: '공개 — WMT 2014 표준 벤치마크 사용',
    },
    anchors: [
      { field: 'results', target: 'table', span: 'EN-DE 28.4 BLEU', label: '표 2' },
      { field: 'method', target: 'section', span: 'Multi-Head Attention', label: '§3.2' },
      { field: 'reproducibility', target: 'section', span: 'tensor2tensor', label: '§6.1' },
    ],
  },
};

// 입문자용(beginner) = SSOT §9.2 정책에 부합: "전문용어 첫 등장 시 괄호 설명 · 약어 첫 등장 시
// 원문 전개 · 이후 등장은 원어 유지". 핵심은 용어를 한글로 음차/치환하지 않고 **영문 원어로 두고**
// 첫 등장 때만 한국어로 괄호 풀이 → 원문·타 자료와 용어 연속성 유지.
export const beginnerSummaryResponse: SummaryOkDTO = {
  ...summaryResponse,
  summary: {
    ...summaryResponse.summary,
    tldr: '기존의 RNN·CNN(recurrent·convolutional neural network, 데이터를 순서대로/지역적으로 처리하던 신경망) 없이, attention(문장에서 단어들 사이의 관련성에 “집중”해 가중치를 매기는 계산)만으로 sequence transduction(한 문장을 다른 문장으로 바꾸는 작업 — 예: 번역)을 수행하는 Transformer를 제안한다. recurrence·convolution을 없애 병렬화가 쉬워 학습이 빠르고, 번역 품질도 당시 최고 수준이다.',
    method:
      'encoder(입력 문장을 이해해 내부 표현으로 바꾸는 부분)와 decoder(그 표현으로 출력 문장을 만드는 부분)를 각각 6개 층으로 쌓는다. 각 층은 multi-head self-attention(여러 관점에서 동시에 단어 간 관련성을 보는 attention)과 position-wise feed-forward network(각 단어를 개별적으로 변환하는 작은 신경망)로 구성된다. 순서 정보는 positional encoding(단어의 위치를 sine·cosine 패턴으로 표시)으로 더한다.',
  },
};

export const abstractTranslationResponse: TranslationOkDTO = {
  status: 'ok',
  task: 'translate',
  meta: { source: 'abstract' },
  cached: false,
  translation: {
    koreanText:
      '지배적인 시퀀스 변환 모델들은 복잡한 순환 신경망이나 합성곱 신경망에 기반한다. 우리는 순환과 합성곱을 완전히 배제하고 오직 어텐션 메커니즘에만 기반한 새로운 단순 네트워크 구조인 Transformer를 제안한다.',
    keptTerms: ['Transformer', 'attention', 'BLEU'],
  },
};

export const fullTranslationResponse: TranslationOkDTO = {
  status: 'ok',
  task: 'translate',
  meta: { source: 'full_text' },
  cached: false,
  translation: {
    koreanText:
      '1. 서론\n순환 신경망, 특히 LSTM과 게이트 순환 신경망은 시퀀스 모델링과 변환 문제에서 최첨단 접근으로 확고히 자리잡았다…\n\n3. 모델 구조\n대부분의 경쟁력 있는 시퀀스 변환 모델은 인코더-디코더 구조를 갖는다. 여기서 인코더는 입력 시퀀스를 연속 표현의 시퀀스로 매핑한다…\n\n(데모용 발췌 — 실제 전문 번역은 논문 전체를 포함합니다.)',
    keptTerms: ['Transformer', 'encoder', 'decoder', 'self-attention'],
  },
};

// Personal glossary (Phase 1/2a) — an in-memory store so the dev preview behaves like the
// real round-trip: upsert remembers termFrom→termTo and bumps a version, and the list reads
// it back so the badge editor pre-fills a previously saved rendering.
const mockGlossary = new Map<string, string>();
let mockGlossaryVer = 0;

export function mockUpsertGlossaryTerm(termFrom: string, termTo: string): GlossaryUpsertResultDTO {
  mockGlossary.set(termFrom, termTo);
  mockGlossaryVer += 1;
  return { status: 'ok', glossaryVer: mockGlossaryVer };
}

export function mockListGlossaryTerms(): GlossaryTermDTO[] {
  return [...mockGlossary.entries()].map(([termFrom, termTo]) => ({ termFrom, termTo }));
}

/** Reset the in-memory glossary so tests start from a clean store (no cross-test bleed). */
export function resetMockGlossary(): void {
  mockGlossary.clear();
  mockGlossaryVer = 0;
}

export const fullTextResponse: FullTextOkDTO = {
  status: 'ok',
  text:
    'Attention Is All You Need\n\n3.2 Multi-Head Attention\nInstead of performing a single attention function with d_model-dimensional keys, values and queries, we found it beneficial to linearly project the queries, keys and values h times with different, learned linear projections…\n\n6.1 Training\nWe trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. Our implementation is available in the tensor2tensor repository.\n\n(데모용 정규화 발췌 — 참고문헌·저자 정보는 제거된 형태입니다.)',
};
