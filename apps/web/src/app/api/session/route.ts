import { type NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

import {
  ACCESS_TOKEN_COOKIE,
  clearSessionCookies,
  createSupabaseAuthClient,
  REFRESH_TOKEN_COOKIE,
  setSessionCookies,
} from '@/lib/supabase-auth';

/**
 * Renews the Supabase session in two HttpOnly cookies. The access token is
 * forwarded to FastAPI; the narrower refresh cookie is sent only to this path.
 * Local development retains the explicitly gated dev-token fallback.
 */

// Server-only: the browser stays on the Vercel origin and never receives the
// backend origin. The same value drives next.config.ts's /api/backend rewrite.
const API_URL = process.env.API_BACKEND_URL ?? 'http://127.0.0.1:3001';

const DevTokenSchema = z.object({
  accessToken: z.string(),
  expiresInSeconds: z.number().int().positive(),
});

export async function POST(request: NextRequest): Promise<NextResponse> {
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;

  if (refreshToken) {
    let supabase: ReturnType<typeof createSupabaseAuthClient>;
    try {
      supabase = createSupabaseAuthClient();
    } catch {
      return NextResponse.json({ error: 'auth_unavailable' }, { status: 503 });
    }
    const { data, error } = await supabase.auth.refreshSession({ refresh_token: refreshToken });
    if (error || !data.session) {
      const response = NextResponse.json({ error: 'invalid_session' }, { status: 401 });
      clearSessionCookies(response);
      return response;
    }
    const response = NextResponse.json({ ok: true } as const);
    setSessionCookies(response, data.session);
    return response;
  }

  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'missing_session' }, { status: 401 });
  }

  const upstream = await fetch(`${API_URL}/auth/dev-token`, {
    method: 'POST',
    cache: 'no-store',
  }).catch(() => null);
  if (!upstream?.ok) {
    return NextResponse.json({ error: 'auth_unavailable' }, { status: 502 });
  }
  const parsed = DevTokenSchema.safeParse(await upstream.json());
  if (!parsed.success) {
    return NextResponse.json({ error: 'auth_contract_mismatch' }, { status: 502 });
  }

  const response = NextResponse.json({ ok: true } as const);
  response.cookies.set('lokara_access_token', parsed.data.accessToken, {
    httpOnly: true,
    sameSite: 'lax',
    secure: false,
    maxAge: parsed.data.expiresInSeconds,
    path: '/',
  });
  return response;
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;

  if (accessToken && refreshToken) {
    try {
      const supabase = createSupabaseAuthClient();
      const { error } = await supabase.auth.setSession({
        access_token: accessToken,
        refresh_token: refreshToken,
      });
      if (!error) await supabase.auth.signOut({ scope: 'local' });
    } catch {
      // Local cookie removal still signs this browser out when Supabase is unavailable.
    }
  }

  const response = NextResponse.json({ ok: true } as const);
  clearSessionCookies(response);
  return response;
}
