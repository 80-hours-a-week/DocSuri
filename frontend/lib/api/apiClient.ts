// ApiClient — single, typed entry point to the backend (LC-2).
//
// All backend access goes through here -> U6 gateway (no direct module calls,
// BR-U5-17). Applies differential retry (idempotent GET only), timeout, and
// in-flight dedup (P-R1, P-P4, BR-U5-18); normalizes failures to UserFacingError.
import type { Transport, TransportRequest, TransportResponse } from './transport';
import { UserFacingError, normalizeHttpError } from './errors';
import { classifySearchResponse, type SearchOutcome } from './classify';
import { recordPath } from '../observability';
import type {
  SearchRequest,
  SignupRequest,
  SignupResult,
  LoginRequest,
  SessionInfo,
} from '@/types/generated';

export interface ApiClientOptions {
  timeoutMs?: number;
  retryBackoffMs?: number;
}

export class ApiClient {
  private readonly timeoutMs: number;
  private readonly retryBackoffMs: number;
  private readonly inflight = new Map<string, Promise<TransportResponse>>();

  constructor(
    private readonly transport: Transport,
    options: ApiClientOptions = {},
  ) {
    this.timeoutMs = options.timeoutMs ?? 8000;
    this.retryBackoffMs = options.retryBackoffMs ?? 200;
  }

  // ---- hero-slice active methods --------------------------------------

  /** Submit a search; returns a classified terminal outcome (FR-11). */
  async search(query: string): Promise<SearchOutcome> {
    const body: SearchRequest = { query };
    const res = await this.request({ method: 'POST', path: '/api/search', body, idempotent: true });
    if (res.status === 200 || res.status === 400) {
      return classifySearchResponse(res.body);
    }
    throw normalizeHttpError(res.status, pick(res.body, 'message'));
  }

  async signup(req: SignupRequest): Promise<SignupResult> {
    const res = await this.request({
      method: 'POST',
      path: '/auth/signup',
      body: req,
      idempotent: false,
    });
    if (res.status === 200 || res.status === 201) return res.body as SignupResult;
    throw normalizeHttpError(res.status, pick(res.body, 'message'));
  }

  async login(req: LoginRequest): Promise<SessionInfo> {
    const res = await this.request({
      method: 'POST',
      path: '/auth/login',
      body: req,
      idempotent: false,
    });
    if (res.status === 200) return res.body as SessionInfo;
    throw normalizeHttpError(res.status, pick(res.body, 'message'));
  }

  async logout(): Promise<void> {
    await this.request({ method: 'POST', path: '/auth/logout', idempotent: false });
  }

  /** Returns the current session, or null when anonymous (401 is not an error). */
  async currentSession(): Promise<SessionInfo | null> {
    const res = await this.request({ method: 'GET', path: '/auth/session', idempotent: true });
    if (res.status === 200) return res.body as SessionInfo;
    if (res.status === 401) return null;
    throw normalizeHttpError(res.status);
  }

  // ---- US-L* stubs (graceful no-op until library UI pass) ----
  // Return empty collections / void so the UI renders "empty state" rather than crashing.

  async listSavedSearches(): Promise<unknown[]> { return []; }
  async saveSearch(): Promise<void> {}
  async deleteSavedSearch(): Promise<void> {}
  async listLibrary(): Promise<unknown[]> { return []; }
  async addToLibrary(): Promise<void> {}
  async removeFromLibrary(): Promise<void> {}
  async listHistory(): Promise<unknown[]> { return []; }

  // ---- internals ------------------------------------------------------

  private async request(req: TransportRequest): Promise<TransportResponse> {
    const key = `${req.method} ${req.path} ${JSON.stringify(req.body ?? null)}`;
    if (req.idempotent) {
      const existing = this.inflight.get(key);
      if (existing) return existing;
    }
    const promise = this.sendWithPolicy(req).finally(() => {
      if (req.idempotent) this.inflight.delete(key);
    });
    if (req.idempotent) this.inflight.set(key, promise);
    return promise;
  }

  private async sendWithPolicy(req: TransportRequest): Promise<TransportResponse> {
    const attempts = req.idempotent ? 2 : 1;
    const stop = recordPath(req.path);
    for (let i = 0; i < attempts; i++) {
      const lastAttempt = i === attempts - 1;
      try {
        const res = await this.withTimeout(this.transport.send(req));
        if (res.status >= 500 && !lastAttempt) {
          await delay(this.retryBackoffMs * (i + 1));
          continue;
        }
        stop(res.status >= 500 ? 'error' : 'ok');
        return res;
      } catch {
        if (!lastAttempt) {
          await delay(this.retryBackoffMs * (i + 1));
          continue;
        }
        stop('error');
        throw new UserFacingError('network');
      }
    }
    // Unreachable, but keeps the type checker happy.
    stop('error');
    throw new UserFacingError('network');
  }

  private withTimeout(p: Promise<TransportResponse>): Promise<TransportResponse> {
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error('timeout')), this.timeoutMs);
      p.then(
        (v) => {
          clearTimeout(t);
          resolve(v);
        },
        (e) => {
          clearTimeout(t);
          reject(e);
        },
      );
    });
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function pick(body: unknown, key: string): unknown {
  return typeof body === 'object' && body !== null ? (body as Record<string, unknown>)[key] : undefined;
}
