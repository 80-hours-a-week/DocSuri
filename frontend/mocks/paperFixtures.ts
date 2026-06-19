// Dev-only paper-metadata fixtures (mock transport layer, same status as
// summarizeFixtures). Production is real-first — these are never shipped; they let
// the detail route render title/authors/abstract while the backend metadata
// endpoint is still PROVISIONAL (NEXT_PUBLIC_DOCSURI_REAL_API unset).
import type { PaperMetaVM } from '@/types/paperMeta';

const META: Record<string, PaperMetaVM> = {
  '1706.03762v5': {
    arxivId: '1706.03762v5',
    title: 'Attention Is All You Need',
    authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit'],
    year: 2017,
    abstract:
      'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    arxivUrl: 'https://arxiv.org/abs/1706.03762',
  },
  '1810.04805v2': {
    arxivId: '1810.04805v2',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    authors: ['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova'],
    year: 2018,
    abstract:
      'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.',
    arxivUrl: 'https://arxiv.org/abs/1810.04805',
  },
  '1512.03385v1': {
    arxivId: '1512.03385v1',
    title: 'Deep Residual Learning for Image Recognition',
    authors: ['Kaiming He', 'Xiangyu Zhang', 'Shaoqing Ren', 'Jian Sun'],
    year: 2015,
    abstract:
      'Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs.',
    arxivUrl: 'https://arxiv.org/abs/1512.03385',
  },
};

/**
 * Returns mock metadata for a known arXiv id, or a generic placeholder for any
 * other id so direct navigation to /paper/[id] still renders a populated header.
 */
export function mockPaperMeta(arxivId: string): PaperMetaVM {
  return (
    META[arxivId] ?? {
      arxivId,
      title: `arXiv 논문 ${arxivId}`,
      authors: ['(데모용 메타데이터)'],
      abstract:
        '데모용 메타데이터입니다. 실제 제목·저자·초록은 백엔드 논문 메타데이터 API 연동 후 표시됩니다.',
      arxivUrl: `https://arxiv.org/abs/${encodeURIComponent(arxivId)}`,
    }
  );
}
