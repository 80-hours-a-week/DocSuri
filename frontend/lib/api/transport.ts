// Transport seam (LC-2, BR-U5-19).
//
// ApiClient depends only on this interface. Today it is backed by MockTransport
// (DTO-derived fixtures). When the U6 gateway + U2 real infra land, swap in
// HttpTransport (server-only) via configuration — no component/ApiClient rewrite.

export type TransportMethod = 'GET' | 'POST' | 'DELETE';

export interface TransportRequest {
  method: TransportMethod;
  path: string;
  body?: unknown;
  /** Safe to retry once on a transient failure (P-R1). */
  idempotent: boolean;
}

export interface TransportResponse {
  status: number;
  body: unknown;
}

export interface Transport {
  send(req: TransportRequest): Promise<TransportResponse>;
}
