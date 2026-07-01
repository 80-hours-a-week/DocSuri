import { describe, expect, it } from 'vitest';
import {
  agentReducer,
  canSend,
  createAttachmentFromFile,
  initialAgentChatState,
  mergeTimelineEvents,
} from '@/lib/agentChat/state';
import type { AgentSessionSummary } from '@/lib/agentChat/types';

const evidenceSession: AgentSessionSummary = {
  id: 's-evidence',
  title: '근거 세션',
  mode: 'evidence',
  state: 'idle',
  updatedAt: '2026-07-01T00:00:00Z',
};

const noveltySession: AgentSessionSummary = {
  id: 's-novelty',
  title: '차별화 세션',
  mode: 'novelty',
  state: 'idle',
  updatedAt: '2026-07-01T00:01:00Z',
};

describe('agent chat reducer/helpers', () => {
  it('locks mode after the first session is selected', () => {
    const selected = agentReducer(initialAgentChatState, {
      type: 'startSession',
      session: evidenceSession,
    });
    const switched = agentReducer(selected, { type: 'startSession', session: noveltySession });

    expect(switched.mode).toBe('evidence');
    expect(switched.session?.id).toBe('s-evidence');
  });

  it('accepts only allowed attachment types within size bounds', () => {
    expect(createAttachmentFromFile({ name: 'paper.pdf', size: 1024 }).status).toBe('ready');
    expect(createAttachmentFromFile({ name: 'draft.md', size: 1024 }).kind).toBe('markdown');
    expect(createAttachmentFromFile({ name: 'slides.pptx', size: 1024 }).status).toBe('rejected');
    expect(createAttachmentFromFile({ name: 'huge.pdf', size: 11 * 1024 * 1024 }).status).toBe(
      'rejected',
    );
  });

  it('keeps timeline events unique and sequence ordered', () => {
    const merged = mergeTimelineEvents(
      [
        { id: 'b', stage: 'two', label: 'B', state: 'running', sequence: 2 },
        { id: 'a', stage: 'one', label: 'A', state: 'running', sequence: 1 },
      ],
      [
        { id: 'b', stage: 'two', label: 'B done', state: 'completed', sequence: 2 },
        { id: 'c', stage: 'three', label: 'C', state: 'completed', sequence: 3 },
      ],
    );

    expect(merged.map((event) => event.id)).toEqual(['a', 'b', 'c']);
    expect(merged[1].label).toBe('B done');
  });

  it('requires a mode, draft, session, and valid attachments before sending', () => {
    const withMode = agentReducer(initialAgentChatState, {
      type: 'startSession',
      session: evidenceSession,
    });
    const withDraft = agentReducer(withMode, { type: 'setDraft', draft: '요약해 주세요' });
    expect(canSend(withDraft)).toBe(true);

    const rejected = agentReducer(withDraft, {
      type: 'addAttachment',
      attachment: createAttachmentFromFile({ name: 'bad.exe', size: 1 }),
    });
    expect(canSend(rejected)).toBe(false);
  });
});
