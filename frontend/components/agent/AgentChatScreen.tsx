'use client';

import { useEffect, useMemo, useReducer, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { UserFacingError, getApiClient } from '@/lib/api';
import {
  agentReducer,
  canSend,
  createAttachmentFromFile,
  createDraftSession,
  createUserMessage,
  initialAgentChatState,
} from '@/lib/agentChat/state';
import type {
  AgentAttachment,
  AgentJobState,
  AgentMessage,
  AgentMode,
  AgentSessionSummary,
  AgentTimelineEvent,
  AgentTimelineState,
} from '@/lib/agentChat/types';
import {
  abstainReasonLabel,
  parseAgentContent,
  type EvidenceResultPayload,
  type EvidenceSourceRef,
} from '@/lib/agentChat/evidenceResult';
import styles from './AgentChatScreen.module.css';

const MODE_LABEL: Record<AgentMode, string> = {
  evidence: 'Research',
  novelty: 'Novelty',
};

const JOB_STATE_LABEL: Record<AgentJobState, string> = {
  idle: '대기',
  queued: '대기',
  running: '진행 중',
  completed: '완료',
  failed: '실패',
  degraded: '저하',
};
const AGENT_REFRESH_MS = 1000;
const STREAM_CHAR_MS = 8;
const SSE_FETCH_TIMEOUT_MS = 5000;
const RESEARCH_MODE_ENABLED =
  !process.env.NEXT_PUBLIC_DOCSURI_REAL_API ||
  process.env.NEXT_PUBLIC_DOCSURI_RESEARCH_AGENT_ENABLED === '1';

export function AgentChatScreen() {
  const api = useMemo(() => getApiClient(), []);
  const [state, dispatch] = useReducer(agentReducer, initialAgentChatState);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const awaitingAgentResponseRef = useRef(false);
  const lastSseEventIdRef = useRef<string | null>(null);
  const seenAgentMessageIdsRef = useRef<Set<string>>(new Set());
  const activeSessionId = state.session?.id;
  const activeMode = state.session?.mode;

  useEffect(() => {
    let alive = true;
    api
      .listAgentSessions()
      .then((sessions) => {
        if (alive) dispatch({ type: 'sessionsLoaded', sessions });
      })
      .catch(() => {
        if (alive) {
          dispatch({
            type: 'sendFailure',
            message: '과거 세션을 불러오지 못했습니다.',
          });
        }
      });
    return () => {
      alive = false;
    };
  }, [api]);

  useEffect(() => {
    lastSseEventIdRef.current = null;
  }, [activeSessionId]);

  useEffect(() => {
    const agentMessageIds = state.messages
      .filter((message) => message.role === 'agent')
      .map((message) => message.id);
    const newestAgentMessageId = agentMessageIds.at(-1);
    const seen = seenAgentMessageIdsRef.current;
    const shouldStream =
      awaitingAgentResponseRef.current &&
      Boolean(newestAgentMessageId) &&
      !seen.has(newestAgentMessageId ?? '');
    for (const id of agentMessageIds) seen.add(id);
    if (shouldStream && newestAgentMessageId) {
      awaitingAgentResponseRef.current = false;
      setStreamingMessageId(newestAgentMessageId);
    }
  }, [state.messages]);

  useEffect(() => {
    if (
      !activeSessionId ||
      !activeSessionId.includes(':') ||
      (state.jobState !== 'queued' && state.jobState !== 'running')
    ) {
      return;
    }
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      try {
        const snapshot = await api.loadAgentSession(activeSessionId);
        if (alive) dispatch({ type: 'refreshSession', snapshot });
      } catch {
        // Keep the last known snapshot; the next user action can retry explicitly.
      } finally {
        if (alive) timer = setTimeout(refresh, AGENT_REFRESH_MS);
      }
    };
    void refresh();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [activeSessionId, api, state.jobState]);

  useEffect(() => {
    if (
      !activeSessionId ||
      activeMode !== 'novelty' ||
      (state.jobState !== 'queued' && state.jobState !== 'running')
    ) {
      return;
    }
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refreshEvents = async () => {
      try {
        const events = await loadNoveltySseEvents(activeSessionId, lastSseEventIdRef.current);
        if (!alive) return;
        if (events.length) {
          lastSseEventIdRef.current = events.at(-1)?.id ?? lastSseEventIdRef.current;
          dispatch({ type: 'eventsReceived', events });
        }
      } catch {
        // The full session poll remains the fallback if the event stream is unavailable.
      } finally {
        if (alive) timer = setTimeout(refreshEvents, AGENT_REFRESH_MS);
      }
    };
    void refreshEvents();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [activeMode, activeSessionId, state.jobState]);

  function startMode(mode: AgentMode) {
    resetStreamingState();
    dispatch({ type: 'startSession', session: createDraftSession(mode) });
  }

  async function loadSession(session: AgentSessionSummary) {
    try {
      resetStreamingState();
      const snapshot = await api.loadAgentSession(session.id);
      dispatch({ type: 'loadSession', snapshot });
      setDrawerOpen(false);
    } catch {
      dispatch({ type: 'sendFailure', message: '세션을 불러오지 못했습니다.' });
    }
  }

  async function deleteSession(session: AgentSessionSummary) {
    try {
      await api.deleteAgentSession(session.id);
      dispatch({ type: 'deleteSession', id: session.id });
    } catch {
      dispatch({ type: 'sendFailure', message: '세션을 삭제하지 못했습니다.' });
    }
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSend(state) || !state.session || !state.mode) return;

    const content = state.draft.trim();
    const attachments = state.attachments.filter((item) => item.status === 'ready');
    const userMessage = createUserMessage(content, attachments);
    awaitingAgentResponseRef.current = true;
    setStreamingMessageId(null);
    dispatch({ type: 'sendStart', message: userMessage });

    try {
      const result = await api.sendAgentMessage(state.session.id, {
        content,
        mode: state.mode,
        attachments,
      });
      dispatch({ type: 'sendSuccess', result });
    } catch (error) {
      awaitingAgentResponseRef.current = false;
      dispatch({
        type: 'sendFailure',
        message:
          error instanceof UserFacingError ? error.message : '에이전트 요청을 처리하지 못했습니다.',
      });
    }
  }

  function attach(files: FileList | null) {
    if (!files) return;
    Array.from(files).forEach((file, idx) => {
      dispatch({
        type: 'addAttachment',
        attachment: createAttachmentFromFile(file, state.attachments.length + idx),
      });
    });
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function resetStreamingState() {
    awaitingAgentResponseRef.current = false;
    seenAgentMessageIdsRef.current = new Set();
    setStreamingMessageId(null);
  }

  return (
    <section
      className={styles.shell}
      data-mode={state.mode ?? undefined}
      data-testid="agent-chat-screen"
    >
      <div className={styles.toolbar}>
        <button
          type="button"
          className={styles.iconButton}
          onClick={() => setDrawerOpen(true)}
          aria-label="과거 세션"
          data-testid="agent-menu"
        >
          <MenuIcon />
        </button>
        <div className={styles.status}>
          <span>{state.mode ? MODE_LABEL[state.mode] : '에이전트'}</span>
          {state.jobState !== 'idle' ? <JobStateBadge state={state.jobState} /> : null}
        </div>
      </div>

      {!state.mode ? (
        <AgentModePicker onSelect={startMode} researchEnabled={RESEARCH_MODE_ENABLED} />
      ) : null}

      <AgentMessageList messages={state.messages} streamingMessageId={streamingMessageId} />
      <AgentProgressTimeline events={state.events} jobState={state.jobState} />

      {state.error ? (
        <p className={styles.error} role="status" data-testid="agent-error">
          {state.error}
        </p>
      ) : null}

      <AgentAttachmentDrawer
        attachments={state.attachments}
        onRemove={(id) => dispatch({ type: 'removeAttachment', id })}
      />

      <form className={styles.composer} onSubmit={submit}>
        <button
          type="button"
          className={styles.attachButton}
          onClick={() => fileInputRef.current?.click()}
          aria-label="파일 추가"
          data-testid="agent-attach-button"
          disabled={!state.mode || state.submitting}
        >
          +
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className={styles.fileInput}
          accept=".pdf,.md,.markdown,.txt,application/pdf,text/plain,text/markdown"
          multiple
          onChange={(e) => attach(e.currentTarget.files)}
          data-testid="agent-file-input"
        />
        <textarea
          className={styles.input}
          value={state.draft}
          onChange={(e) => dispatch({ type: 'setDraft', draft: e.target.value })}
          placeholder={state.mode ? '메시지를 입력하세요' : '먼저 모드를 선택하세요'}
          aria-label="에이전트 메시지"
          data-testid="agent-composer-input"
          disabled={!state.mode || state.submitting}
          rows={1}
        />
        <button
          type="submit"
          className={styles.sendButton}
          disabled={!canSend(state)}
          data-testid="agent-composer-submit"
        >
          전송
        </button>
      </form>

      {drawerOpen ? (
        <AgentSessionDrawer
          sessions={state.sessions}
          activeId={state.session?.id ?? null}
          onClose={() => setDrawerOpen(false)}
          onNew={() => {
            resetStreamingState();
            dispatch({ type: 'newChat' });
            setDrawerOpen(false);
          }}
          onLoad={loadSession}
          onDelete={deleteSession}
        />
      ) : null}
    </section>
  );
}

function AgentModePicker({
  onSelect,
  researchEnabled,
}: {
  onSelect: (mode: AgentMode) => void;
  researchEnabled: boolean;
}) {
  return (
    <div className={styles.modePicker} data-testid="agent-mode-picker">
      <button
        type="button"
        onClick={() => onSelect('evidence')}
        disabled={!researchEnabled}
        aria-label={researchEnabled ? 'Research' : 'Research 준비 중'}
        data-mode="evidence"
        data-testid="agent-mode-evidence"
      >
        <strong>Research</strong>
        <span>작성 논문 근거 형성</span>
      </button>
      <button
        type="button"
        onClick={() => onSelect('novelty')}
        data-mode="novelty"
        data-testid="agent-mode-novelty"
      >
        <strong>Novelty</strong>
        <span>유사도 검사 및 차별점 추천</span>
      </button>
    </div>
  );
}

function AgentSessionDrawer({
  sessions,
  activeId,
  onClose,
  onNew,
  onLoad,
  onDelete,
}: {
  sessions: AgentSessionSummary[];
  activeId: string | null;
  onClose: () => void;
  onNew: () => void;
  onLoad: (session: AgentSessionSummary) => void;
  onDelete: (session: AgentSessionSummary) => void;
}) {
  return (
    <div className={styles.drawerOverlay} data-testid="agent-session-drawer">
      <aside className={styles.drawer} aria-label="과거 세션">
        <div className={styles.drawerHeader}>
          <button type="button" onClick={onNew} data-testid="agent-session-new">
            새 채팅
          </button>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>
        <div className={styles.sessionList}>
          {sessions.map((session) => (
            <div
              key={session.id}
              className={styles.sessionRow}
              data-active={session.id === activeId}
              data-mode={session.mode}
            >
              <button type="button" onClick={() => onLoad(session)}>
                <span>{session.title}</span>
                <small>
                  {MODE_LABEL[session.mode]} · {JOB_STATE_LABEL[session.state]} ·{' '}
                  {formatSessionUpdatedAt(session.updatedAt)}
                </small>
              </button>
              <button
                type="button"
                className={styles.deleteButton}
                onClick={() => onDelete(session)}
                aria-label={`${session.title} 삭제`}
              >
                삭제
              </button>
            </div>
          ))}
          {sessions.length === 0 ? <p className={styles.empty}>저장된 세션이 없습니다.</p> : null}
        </div>
      </aside>
    </div>
  );
}

function AgentMessageList({
  messages,
  streamingMessageId,
}: {
  messages: AgentMessage[];
  streamingMessageId: string | null;
}) {
  return (
    <div className={styles.messages} data-testid="agent-message-list">
      {messages.length === 0 ? <p className={styles.empty}>대화를 시작하세요.</p> : null}
      {messages.map((message) => (
        <AgentMessageItem
          key={message.id}
          message={message}
          streaming={message.id === streamingMessageId}
        />
      ))}
    </div>
  );
}

function AgentMessageItem({ message, streaming }: { message: AgentMessage; streaming: boolean }) {
  return (
    <article
      className={styles.message}
      data-role={message.role}
      data-status={message.status ?? 'sent'}
      data-streaming={streaming && message.role === 'agent'}
      data-testid="agent-message"
    >
      <AgentMessageContent message={message} streaming={streaming} />
      {message.attachments?.length ? (
        <div className={styles.messageFiles}>
          {message.attachments.map((file) => (
            <span key={file.id}>{file.name}</span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function AgentMessageContent({
  message,
  streaming,
}: {
  message: AgentMessage;
  streaming: boolean;
}) {
  // evidence orchestrator 결과(JSON/[abstain]/[error])는 agent(assistant) 메시지에서만 나온다.
  // 사용자가 타이핑한 텍스트가 우연히 JSON처럼 보여도 파싱을 시도하지 않도록 role로 분기한다.
  if (message.role !== 'agent') {
    return <p>{message.content}</p>;
  }

  const parsed = parseAgentContent(message.content);

  // 구조화 결과(근거 카드/보류/오류)는 스트리밍하지 않고 즉시 렌더링한다 — JSON을 한 글자씩
  // 노출하면 완성 전까지 깨져 보인다. 일반 텍스트 답변만 타자기 효과로 스트리밍한다.
  if (parsed.kind === 'evidence') {
    return <EvidenceResultView result={parsed.result} />;
  }
  if (parsed.kind === 'abstain') {
    return <p className={styles.abstainNotice}>{abstainReasonLabel(parsed.reason)}</p>;
  }
  if (parsed.kind === 'error') {
    return <p className={styles.abstainNotice}>일시적인 오류로 답변을 생성하지 못했습니다.</p>;
  }
  return <StreamingText text={parsed.text} streaming={streaming} />;
}

function StreamingText({ text, streaming }: { text: string; streaming: boolean }) {
  const visible = useStreamingText(text, streaming);
  return <p>{visible}</p>;
}

function useStreamingText(content: string, enabled: boolean): string {
  const [visible, setVisible] = useState(enabled ? '' : content);

  useEffect(() => {
    if (!enabled) {
      setVisible(content);
      return;
    }
    let index = 0;
    setVisible('');
    const timer = setInterval(() => {
      index += 1;
      setVisible(content.slice(0, index));
      if (index >= content.length) clearInterval(timer);
    }, STREAM_CHAR_MS);
    return () => clearInterval(timer);
  }, [content, enabled]);

  return visible;
}

function EvidenceResultView({ result }: { result: EvidenceResultPayload }) {
  if (result.claims.length === 0) {
    return <p className={styles.abstainNotice}>제시할 수 있는 근거를 찾지 못했습니다.</p>;
  }
  return (
    <div className={styles.evidenceClaims}>
      {result.claims.map((claim, idx) => (
        <article key={idx} className={styles.evidenceClaim}>
          <p className={styles.evidenceStatement}>{claim.statement}</p>
          <EvidenceRefList refs={claim.supporting} />
          {claim.conflicting.length > 0 ? (
            <div className={styles.evidenceConflict}>
              <strong>상충하는 근거</strong>
              <EvidenceRefList refs={claim.conflicting} />
            </div>
          ) : null}
        </article>
      ))}
      <p className={styles.evidenceCoverage}>
        참고 논문 {result.coverage.paperCount}편
        {result.coverage.queryUsed ? ` · 검색어: ${result.coverage.queryUsed}` : ''}
      </p>
    </div>
  );
}

function EvidenceRefList({ refs }: { refs: EvidenceSourceRef[] }) {
  if (refs.length === 0) return null;
  return (
    <ul className={styles.evidenceRefs}>
      {refs.map((ref, idx) => (
        <li key={idx} className={styles.evidenceRef}>
          <span className={styles.evidenceSource}>
            <span className={styles.evidencePaperId}>{ref.paperId}</span>
            {/* 인용 앵커(#339). recordRef는 내부 식별자라 노출하지 않는다. */}
            {ref.anchor ? <span className={styles.evidenceAnchor}>§ {ref.anchor}</span> : null}
          </span>
          {ref.quote ? <blockquote>{ref.quote}</blockquote> : null}
        </li>
      ))}
    </ul>
  );
}

function AgentProgressTimeline({
  events,
  jobState,
}: {
  events: AgentTimelineEvent[];
  jobState: AgentJobState;
}) {
  if (events.length === 0) return null;
  const displayEvents = normalizeTimelineDisplay(events, jobState);
  return (
    <section className={styles.timeline} aria-label="탐구 프로세스" data-testid="agent-timeline">
      {displayEvents.map((event) => (
        <AgentTimelineItem key={event.id} event={event} />
      ))}
    </section>
  );
}

export function normalizeTimelineDisplay(
  events: AgentTimelineEvent[],
  jobState: AgentJobState = 'running',
): AgentTimelineEvent[] {
  let lastTerminalIndex = -1;
  for (let i = events.length - 1; i >= 0; i -= 1) {
    if (events[i].state !== 'running') {
      lastTerminalIndex = i;
      break;
    }
  }
  if (lastTerminalIndex < 0 && isTerminalJobState(jobState)) {
    return events.map((event) =>
      event.state === 'running' ? { ...event, state: 'completed' } : event,
    );
  }
  if (lastTerminalIndex <= 0) return events;
  return events.map((event, index) =>
    index < lastTerminalIndex && event.state === 'running'
      ? { ...event, state: 'completed' satisfies AgentTimelineState }
      : event,
  );
}

function isTerminalJobState(state: AgentJobState): boolean {
  return state === 'completed' || state === 'failed' || state === 'degraded';
}

async function loadNoveltySseEvents(
  sessionId: string,
  afterEventId: string | null,
): Promise<AgentTimelineEvent[]> {
  const url = noveltySseUrl(sessionId, afterEventId);
  if (!url) return [];
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SSE_FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      headers: { accept: 'text/event-stream' },
      credentials: 'same-origin',
      cache: 'no-store',
      signal: controller.signal,
    });
    if (!res.ok) return [];
    return parseNoveltySseEvents(await res.text());
  } finally {
    clearTimeout(timer);
  }
}

function noveltySseUrl(sessionId: string, afterEventId: string | null): string | null {
  const prefix = 'novelty:';
  if (!sessionId.startsWith(prefix)) return null;
  const rawId = sessionId.slice(prefix.length);
  if (!rawId) return null;
  const params = new URLSearchParams();
  if (afterEventId) params.set('after', afterEventId);
  const query = params.toString();
  return `/bff/api/novelty/jobs/${encodeURIComponent(rawId)}/events${query ? `?${query}` : ''}`;
}

export function parseNoveltySseEvents(text: string): AgentTimelineEvent[] {
  return text
    .split(/\r?\n\r?\n/)
    .map(parseSseBlock)
    .filter((event): event is AgentTimelineEvent => Boolean(event));
}

function parseSseBlock(block: string): AgentTimelineEvent | null {
  let eventName = 'message';
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) eventName = line.slice('event:'.length).trim();
    if (line.startsWith('data:')) data.push(line.slice('data:'.length).trimStart());
  }
  if (eventName !== 'progress' || data.length === 0) return null;
  try {
    const raw = JSON.parse(data.join('\n'));
    return mapSseProgressEvent(raw);
  } catch {
    return null;
  }
}

function mapSseProgressEvent(raw: unknown): AgentTimelineEvent | null {
  if (!raw || typeof raw !== 'object') return null;
  const record = raw as Record<string, unknown>;
  const id = stringValue(record.eventId);
  const stage = stringValue(record.state) ?? 'running';
  if (!id) return null;
  return {
    id,
    stage,
    label: stringValue(record.message) ?? stage,
    state: mapSseTimelineState(stage),
  };
}

function mapSseTimelineState(stage: string): AgentTimelineState {
  if (stage === 'failed' || stage === 'cancelled') return 'failed';
  if (stage === 'degraded') return 'degraded';
  if (stage === 'completed') return 'completed';
  return 'running';
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

function AgentTimelineItem({ event }: { event: AgentTimelineEvent }) {
  const [open, setOpen] = useState(event.state === 'running' || event.state === 'degraded');
  return (
    <details
      className={styles.timelineEvent}
      data-state={event.state}
      data-testid="agent-timeline-event"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>
        <span>{event.label}</span>
        <JobStateBadge state={event.state} />
      </summary>
      {event.detail ? <p>{event.detail}</p> : null}
    </details>
  );
}

function JobStateBadge({ state }: { state: AgentTimelineState | AgentJobState }) {
  return (
    <small className={styles.stateBadge} data-state={state}>
      {state === 'queued' || state === 'running' ? (
        <span className={styles.spinner} aria-hidden="true" />
      ) : null}
      {JOB_STATE_LABEL[state]}
    </small>
  );
}

function AgentAttachmentDrawer({
  attachments,
  onRemove,
}: {
  attachments: AgentAttachment[];
  onRemove: (id: string) => void;
}) {
  if (attachments.length === 0) return null;
  return (
    <div className={styles.attachments} data-testid="agent-attachment-drawer">
      {attachments.map((attachment) => (
        <div key={attachment.id} className={styles.attachment} data-status={attachment.status}>
          <span>{attachment.name}</span>
          {attachment.error ? <small>{attachment.error}</small> : null}
          <button type="button" onClick={() => onRemove(attachment.id)} aria-label="첨부 제거">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

function MenuIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </svg>
  );
}

function formatSessionUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
