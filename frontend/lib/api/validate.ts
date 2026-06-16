// Client-side input validation (UX aid only; backend is authoritative).
// BR-U5-1/2/3, SEC-5.

export const MAX_QUERY_LENGTH = 500;

export type ValidationResult =
  | { ok: true; value: string }
  | { ok: false; message: string };

/** Validate + normalize a search query (FR-1, SEC-5). NFC-normalize, trim. */
export function validateQuery(raw: string): ValidationResult {
  const value = raw.normalize('NFC').trim();
  if (value.length === 0) {
    return { ok: false, message: '검색어를 입력해 주세요.' };
  }
  if (value.length > MAX_QUERY_LENGTH) {
    return { ok: false, message: `검색어는 ${MAX_QUERY_LENGTH}자 이하로 입력해 주세요.` };
  }
  return { ok: true, value };
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Shape check mirrored from accounts.schema.json (policy stays server-side). */
export function validateEmail(raw: string): ValidationResult {
  const value = raw.trim();
  if (value.length === 0) return { ok: false, message: '이메일을 입력해 주세요.' };
  if (!EMAIL_RE.test(value)) return { ok: false, message: '올바른 이메일 형식이 아닙니다.' };
  return { ok: true, value };
}

/** Presence check only — complexity/blacklist policy is delegated to U3 (BR-U5-2). */
export function validateRequiredPassword(raw: string): ValidationResult {
  if (raw.length === 0) return { ok: false, message: '비밀번호를 입력해 주세요.' };
  return { ok: true, value: raw };
}
