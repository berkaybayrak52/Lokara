/** Claims the API relies on after JWT verification. */
export interface AuthContext {
  /** Supabase user id (JWT `sub`) — maps onto Person at M5. */
  readonly personId: string;
  /** The account whose data this request may touch. Drives the RLS context. */
  readonly accountId: string;
}

export interface AuthenticatedRequest extends Express.Request {
  auth?: AuthContext;
}
