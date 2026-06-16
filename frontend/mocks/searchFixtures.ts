// Mock search fixtures — derived from shared/dtos/search.schema.json (BR-U5-19).
// Exercises every SearchResponse branch. Cross-lingual sample: a Korean query
// surfaces English arXiv papers (TD-3, MR-2). Only the 7 card fields appear.
import type {
  SearchResultPageDTO,
  AbstainDTO,
  DegradedResultDTO,
  ValidationErrorDTO,
  ResultCardVM,
} from '@/types/generated';

const CARDS: ResultCardVM[] = [
  {
    title: 'Attention Is All You Need',
    authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar'],
    year: 2017,
    arxivId: '1706.03762v5',
    abstractSnippet:
      'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks…',
    relevance: '높음',
    arxivUrl: 'https://arxiv.org/abs/1706.03762',
  },
  {
    title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    authors: ['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova'],
    year: 2018,
    arxivId: '1810.04805v2',
    abstractSnippet:
      'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations…',
    relevance: '높음',
    arxivUrl: 'https://arxiv.org/abs/1810.04805',
  },
  {
    title: 'Deep Residual Learning for Image Recognition',
    authors: ['Kaiming He', 'Xiangyu Zhang', 'Shaoqing Ren', 'Jian Sun'],
    year: 2015,
    arxivId: '1512.03385v1',
    abstractSnippet:
      'Deeper neural networks are more difficult to train. We present a residual learning framework…',
    relevance: '보통',
    arxivUrl: 'https://arxiv.org/abs/1512.03385',
  },
];

export const pageResponse: SearchResultPageDTO = {
  cards: CARDS,
  meta: { resultCount: CARDS.length, degraded: false },
};

export const emptyResponse: SearchResultPageDTO = {
  cards: [],
  meta: { resultCount: 0, degraded: false },
};

export const abstainResponse: AbstainDTO = {
  reason: 'out-of-corpus',
};

export const degradedResponse: DegradedResultDTO = {
  cards: CARDS.slice(0, 2),
  meta: { resultCount: 2, degraded: true, degradationMode: 'lexical-only' },
  mode: 'lexical-only',
};

export const validationErrorResponse: ValidationErrorDTO = {
  field: 'query',
  message: '검색어를 확인해 주세요.',
};
