import 'server-only';
import type { Transport, TransportRequest, TransportResponse } from './transport';

// HttpTransport (LC-2, P-S1) — SERVER-ONLY.
//
// `import 'server-only'` makes a client-side import a build error: the gateway
// base URL and the httpOnly session cookie never reach the browser bundle
// (SEC-3/12). Forwards the incoming session cookie to the U6 gateway; the token
// lives only in the server<->gateway hop.
//
// Inert until the U6 gateway is deployed — the app runs on MockTransport today.
// Swapping mock -> http is a configuration change (see lib/api/index.ts).

export interface HttpTransportConfig {
  baseUrl: string;
  /** The raw Cookie header captured server-side from the inbound request. */
  cookieHeader?: string;
}

export class HttpTransport implements Transport {
  constructor(private readonly config: HttpTransportConfig) {}

  async send(req: TransportRequest): Promise<TransportResponse> {
    const headers: Record<string, string> = { 'content-type': 'application/json' };
    if (this.config.cookieHeader) headers['cookie'] = this.config.cookieHeader;

    const res = await fetch(`${this.config.baseUrl}${req.path}`, {
      method: req.method,
      headers,
      body: req.body !== undefined ? JSON.stringify(req.body) : undefined,
      // Never cache personalized/authenticated responses (P-P3).
      cache: 'no-store',
    });

    let body: unknown = null;
    const text = await res.text();
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = null;
      }
    }
    return { status: res.status, body };
  }
}
