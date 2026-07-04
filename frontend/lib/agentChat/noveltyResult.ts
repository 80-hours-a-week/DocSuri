// novelty result(JSON-in-content) 타입과 가드 — evidence 결과와 동일한 seam으로
// 구조화 아티팩트를 메시지 content에 실어 세션 영속/재열람에서도 구조를 유지한다.

export interface NoveltySourceRef {
  type?: string | null;
  identifier?: string | null;
  title?: string | null;
  url?: string | null;
}

export interface NoveltyPayloadItem {
  title?: string;
  summary?: string;
  rationale?: string;
  riskType?: string;
  evidenceStatus?: string;
  sourceRefs?: NoveltySourceRef[];
}

export interface NoveltyArtifact {
  artifactId: string;
  kind: string;
  title: string;
  payload: Record<string, unknown>;
  createdAt?: string;
}

export interface NoveltyResultPayload {
  kind: 'novelty';
  artifacts: NoveltyArtifact[];
}

export function isNoveltyResultPayload(value: unknown): value is NoveltyResultPayload {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return candidate.kind === 'novelty' && Array.isArray(candidate.artifacts);
}

// payload.items — 백엔드 LLM/similarity 어댑터의 공통 컨벤션({ items: [...] }).
export function itemsOf(payload: Record<string, unknown>): NoveltyPayloadItem[] {
  const items = payload.items;
  return Array.isArray(items) ? (items as NoveltyPayloadItem[]) : [];
}

export function sourceRefsOf(value: unknown): NoveltySourceRef[] {
  return Array.isArray(value) ? (value as NoveltySourceRef[]) : [];
}

export function textField(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  return typeof value === 'string' ? value : '';
}

export function listField(payload: Record<string, unknown>, key: string): string[] {
  const value = payload[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string');
}
