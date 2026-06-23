// Structural classification of the /api/summarize response union (FR-12~14, BR-SF-14).
//
// Unlike the search response, the summarize union carries a `status` discriminant,
// so we branch on it directly. Terminal outcomes only — progressive streaming is a
// transport-seam extension (fast-follow); v1 classifies the completed body.
import type { SummaryVM, TranslationVM, SummaryMeta, AssetRef } from '@/types/generated';

export type SummarizeOutcome =
  | { kind: 'summary'; summary: SummaryVM; meta: SummaryMeta; cached: boolean }
  | { kind: 'translation'; translation: TranslationVM; meta: SummaryMeta; cached: boolean }
  | { kind: 'abstain'; reason: unknown }
  | { kind: 'degraded'; message: string }
  | { kind: 'sourceUnavailable'; reason: unknown }
  | { kind: 'invalid'; field?: string; message: string }
  | { kind: 'error'; message: string };

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null;
}

export function classifySummarizeResponse(body: unknown): SummarizeOutcome {
  if (!isRecord(body)) {
    return { kind: 'error', message: '결과를 해석할 수 없습니다.' };
  }
  switch (body.status) {
    case 'ok': {
      const meta = (isRecord(body.meta) ? body.meta : {}) as SummaryMeta;
      const cached = Boolean(body.cached);
      if ('summary' in body) {
        return { kind: 'summary', summary: body.summary as SummaryVM, meta, cached };
      }
      if ('translation' in body) {
        return { kind: 'translation', translation: body.translation as TranslationVM, meta, cached };
      }
      return { kind: 'error', message: '결과를 해석할 수 없습니다.' };
    }
    case 'abstain':
      return { kind: 'abstain', reason: body.reason };
    case 'cost_degraded':
      return {
        kind: 'degraded',
        message: typeof body.message === 'string' ? body.message : 'AI 요약이 일시 중단됐어요.',
      };
    case 'source_unavailable':
      return { kind: 'sourceUnavailable', reason: body.reason };
    case 'validation_error':
      // Gap #2: backend now carries a message → surface the "check your input" path.
      return {
        kind: 'invalid',
        field: typeof body.field === 'string' ? body.field : undefined,
        message: typeof body.message === 'string' ? body.message : '입력을 확인해 주세요.',
      };
    case 'unauthorized':
      // Gap #3: 401 maps to a clear auth message, not a generic "couldn't read result".
      return { kind: 'error', message: '로그인이 필요합니다.' };
    default:
      if ('message' in body) {
        return {
          kind: 'invalid',
          field: typeof body.field === 'string' ? body.field : undefined,
          message: typeof body.message === 'string' ? body.message : '입력을 확인해 주세요.',
        };
      }
      return { kind: 'error', message: '결과를 해석할 수 없습니다.' };
  }
}

// ---- Full-text (Q5=C, provisional) ----

export type FullTextOutcome =
  | { kind: 'page'; text: string }
  | { kind: 'licenseUnavailable' }
  | { kind: 'sourceUnavailable' }
  | { kind: 'error'; message: string };

export function classifyFullTextResponse(body: unknown): FullTextOutcome {
  if (!isRecord(body)) {
    return { kind: 'error', message: '원문을 불러올 수 없습니다.' };
  }
  switch (body.status) {
    case 'ok':
      return { kind: 'page', text: typeof body.text === 'string' ? body.text : '' };
    case 'license_unavailable':
      return { kind: 'licenseUnavailable' };
    case 'source_unavailable':
      return { kind: 'sourceUnavailable' };
    default:
      return { kind: 'error', message: '원문을 불러올 수 없습니다.' };
  }
}

// ---- Figure/table assets (FR-17, display-only) ----

export type AssetsOutcome =
  | { kind: 'assets'; assets: AssetRef[] }
  | { kind: 'licenseUnavailable' }
  | { kind: 'unauthorized' }
  | { kind: 'error'; message: string };

export function classifyAssetsResponse(body: unknown): AssetsOutcome {
  if (!isRecord(body)) {
    return { kind: 'error', message: '그림·도표를 불러올 수 없습니다.' };
  }
  switch (body.status) {
    case 'ok':
      return { kind: 'assets', assets: Array.isArray(body.assets) ? (body.assets as AssetRef[]) : [] };
    case 'license_unavailable':
      return { kind: 'licenseUnavailable' };
    case 'unauthorized':
      return { kind: 'unauthorized' };
    default:
      return { kind: 'error', message: '그림·도표를 불러올 수 없습니다.' };
  }
}
