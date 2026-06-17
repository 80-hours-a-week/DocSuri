// ApiClient factory (BR-U5-19).
//
// Selects the transport by configuration:
//   - DOCSURI_GATEWAY_URL set → HttpTransport (server-only, real backend)
//   - unset / empty           → MockTransport (DTO-derived fixtures)
//
// Components call getApiClient() and are transport-agnostic.
import { ApiClient } from './apiClient';
import { MockTransport } from './mockTransport';
import type { Transport } from './transport';

export { ApiClient } from './apiClient';
export { UserFacingError } from './errors';
export type { SearchOutcome } from './classify';
export type { Transport } from './transport';

let mockSingleton: ApiClient | null = null;

/** Mock-first client (browser + server while the gateway is undeployed). */
export function getMockApiClient(): ApiClient {
  if (!mockSingleton) mockSingleton = new ApiClient(new MockTransport());
  return mockSingleton;
}

/**
 * Resolve the active ApiClient based on environment.
 *
 * Server-side (DOCSURI_GATEWAY_URL set): lazily imports HttpTransport so the
 * `server-only` guard fires only on this path. Pass `cookieHeader` from the
 * inbound request to forward the session cookie.
 *
 * Client-side or gateway-undeployed: falls back to MockTransport.
 */
export async function getServerApiClient(cookieHeader?: string): Promise<ApiClient> {
  const gatewayUrl = process.env.DOCSURI_GATEWAY_URL;
  if (gatewayUrl) {
    const { HttpTransport } = await import('./httpTransport');
    return new ApiClient(new HttpTransport({ baseUrl: gatewayUrl, cookieHeader }));
  }
  return getMockApiClient();
}

/**
 * Synchronous variant — returns mock when gateway is undeployed, or accepts
 * an explicitly constructed transport (for tests / client components).
 */
export function getApiClient(transport?: Transport): ApiClient {
  if (transport) return new ApiClient(transport);
  return getMockApiClient();
}
