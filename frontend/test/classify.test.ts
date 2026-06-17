import { describe, it, expect } from 'vitest';
import { classifySearchResponse } from '@/lib/api/classify';
import {
  pageResponse,
  emptyResponse,
  abstainResponse,
  degradedResponse,
  validationErrorResponse,
} from '@/mocks/searchFixtures';

describe('classifySearchResponse', () => {
  it('classifies a result page', () => {
    expect(classifySearchResponse(pageResponse).kind).toBe('page');
  });

  it('classifies an empty page distinctly from abstain', () => {
    expect(classifySearchResponse(emptyResponse).kind).toBe('empty');
    expect(classifySearchResponse(abstainResponse).kind).toBe('abstain');
  });

  it('classifies a degraded response', () => {
    const out = classifySearchResponse(degradedResponse);
    expect(out.kind).toBe('degraded');
  });

  it('classifies a validation error', () => {
    expect(classifySearchResponse(validationErrorResponse).kind).toBe('invalid');
  });

  it('fails closed on garbage', () => {
    expect(classifySearchResponse(null).kind).toBe('invalid');
    expect(classifySearchResponse(42).kind).toBe('invalid');
  });
});
