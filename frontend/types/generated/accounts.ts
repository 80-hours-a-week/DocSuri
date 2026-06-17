/* Curated from shared/dtos/accounts.schema.json (exposed contract). Run `pnpm gen:types`
 * to refresh the raw schema dump under types/.schema-raw/ for drift review.
 * Producer: U3 Accounts. Consumer: U5. SEC-12/3: `password` is request-input-only. */

/** Self-signup input. `password` is INPUT-ONLY and never logged/returned (SEC-12/3). */
export interface SignupRequest {
  email: string;
  password: string;
}

/** Signup success — new account identifier only. */
export interface SignupResult {
  accountId: unknown;
}

/** Login input. `password` is INPUT-ONLY. Failures surface as generalized auth errors. */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Non-sensitive session info (front-end session sync). The session token itself
 * is carried by the secure httpOnly cookie (transport), NOT by this body DTO.
 */
export interface SessionInfo {
  userId: string;
  /** RFC 3339 / ISO 8601 date-time. */
  expiresAt: string;
}
