export const AGENT_MODES = ['evidence', 'novelty'] as const;

export type AgentMode = (typeof AGENT_MODES)[number];
export type AgentJobState = 'idle' | 'queued' | 'running' | 'completed' | 'failed' | 'degraded';
export type AgentMessageRole = 'user' | 'agent';
export type AgentAttachmentKind = 'pdf' | 'markdown' | 'text' | 'unknown';
export type AgentAttachmentStatus = 'ready' | 'reading' | 'rejected';
export type AgentTimelineState = 'running' | 'completed' | 'failed' | 'degraded';

export interface AgentAttachment {
  id: string;
  name: string;
  kind: AgentAttachmentKind;
  sizeBytes: number;
  status: AgentAttachmentStatus;
  error?: string;
  /** US-EV4(#268)/US-NV2(#252) — md/txt 본문(≤256KiB). PDF는 본문 분석 후속이라 없음. */
  contentText?: string;
}

export interface AgentTimelineEvent {
  id: string;
  stage: string;
  label: string;
  detail?: string;
  state: AgentTimelineState;
  sequence?: number;
  source?: string;
}

export interface AgentMessage {
  id: string;
  role: AgentMessageRole;
  content: string;
  createdAt: string;
  attachments?: AgentAttachment[];
  status?: 'pending' | 'sent' | 'failed';
}

export interface AgentSessionSummary {
  id: string;
  title: string;
  mode: AgentMode;
  state: AgentJobState;
  updatedAt: string;
}

export interface AgentSessionSnapshot {
  session: AgentSessionSummary;
  messages: AgentMessage[];
  events: AgentTimelineEvent[];
}

export interface AgentSessionListResponse {
  sessions: AgentSessionSummary[];
}

export interface AgentSendMessageRequest {
  content: string;
  mode: AgentMode;
  attachments?: AgentAttachment[];
}

export interface AgentSendMessageResult {
  session: AgentSessionSummary;
  messages: AgentMessage[];
  events: AgentTimelineEvent[];
  outcome: AgentJobState;
  retryable?: boolean;
  errorMessage?: string;
}
