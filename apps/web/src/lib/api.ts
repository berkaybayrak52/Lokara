import type { z } from 'zod';

/**
 * The shared API interceptor (docs/04 "Auth in one api.ts interceptor").
 *
 * Web transport: the JWT lives in an HttpOnly cookie set by the Next route
 * handler /api/session — JS never sees the token. Requests go to FastAPI with
 * credentials so the cookie rides along (same-site: same host, other port).
 *
 * 401 handling: refresh the session once, replay the failed request once,
 * never double-fire — concurrent 401s share a single in-flight refresh
 * (mobile reuses this logic with Bearer/secure-storage instead of the cookie).
 */

/** Exported for the rare non-JSON case (PDF download links). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    /**
     * FastAPI's `detail`, when the response carried one. Some rejections are
     * only explainable by the server (which file types it reads, how large an
     * upload may be) — re-authoring those sentences in the client would let
     * the two drift apart.
     */
    readonly detail?: string,
  ) {
    super(`API request failed: ${status} ${path}`);
    this.name = 'ApiError';
  }
}

/** Best-effort: an error body is a courtesy, never something to depend on. */
async function readDetail(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const { detail } = body as { detail: unknown };
      return typeof detail === 'string' ? detail : undefined;
    }
  } catch {
    /* not JSON, or already consumed — fall through to the status alone */
  }
  return undefined;
}

let refreshInFlight: Promise<boolean> | null = null;

/** TODO(supabase): at M5 this exchanges the Supabase refresh token instead. */
async function refreshSession(): Promise<boolean> {
  try {
    const response = await fetch('/api/session', { method: 'POST', cache: 'no-store' });
    return response.ok;
  } catch {
    return false;
  }
}

function rawFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    cache: 'no-store',
    credentials: 'include', // sends the HttpOnly session cookie to the API
    ...init,
  });
}

export async function api<Schema extends z.ZodType>(
  path: string,
  schema: Schema,
  init?: RequestInit,
): Promise<z.infer<Schema>> {
  let response = await rawFetch(path, init);

  if (response.status === 401) {
    // Single-flight: every concurrently failing request awaits the SAME
    // refresh; the promise is cleared afterwards so a later 401 may refresh again.
    refreshInFlight ??= refreshSession().finally(() => {
      refreshInFlight = null;
    });
    const refreshed = await refreshInFlight;
    if (!refreshed) {
      throw new ApiError(401, path);
    }
    response = await rawFetch(path, init); // replay exactly once — a second 401 falls through
  }

  if (!response.ok) {
    throw new ApiError(response.status, path, await readDetail(response));
  }
  // 204 has no body — parse `undefined` so the caller still declares a schema
  // (z.undefined()) instead of the call silently skipping validation.
  if (response.status === 204) {
    return schema.parse(undefined) as z.infer<Schema>;
  }
  return schema.parse(await response.json()) as z.infer<Schema>;
}
