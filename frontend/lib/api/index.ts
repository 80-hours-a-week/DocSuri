// ApiClient factory (BR-U5-19).
//
// Selects the transport by configuration. Today: MockTransport (DTO-derived
// fixtures). When the U6 gateway is deployed, set DOCSURI_GATEWAY_URL and the
// server path will use HttpTransport — components/ApiClient are untouched.
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
 * Resolve the active ApiClient. The HttpTransport branch is intentionally
 * loaded lazily and server-side only (it imports `server-only`).
 */
export function getApiClient(transport?: Transport): ApiClient {
  if (transport) return new ApiClient(transport);
  return getMockApiClient();
}
