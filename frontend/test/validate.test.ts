import { describe, it, expect } from 'vitest';
import {
  validateQuery,
  validateEmail,
  validateRequiredPassword,
  MAX_QUERY_LENGTH,
} from '@/lib/api/validate';

describe('validateQuery', () => {
  it('rejects empty / whitespace', () => {
    expect(validateQuery('   ').ok).toBe(false);
  });
  it('rejects over the max length', () => {
    expect(validateQuery('a'.repeat(MAX_QUERY_LENGTH + 1)).ok).toBe(false);
  });
  it('trims and NFC-normalizes a valid query', () => {
    const res = validateQuery('  transformer  ');
    expect(res).toEqual({ ok: true, value: 'transformer' });
  });
});

describe('validateEmail', () => {
  it('rejects malformed', () => {
    expect(validateEmail('nope').ok).toBe(false);
  });
  it('accepts a basic address', () => {
    expect(validateEmail('a@b.co').ok).toBe(true);
  });
});

describe('validateRequiredPassword', () => {
  it('requires presence only (policy is server-side)', () => {
    expect(validateRequiredPassword('').ok).toBe(false);
    expect(validateRequiredPassword('x').ok).toBe(true);
  });
});
