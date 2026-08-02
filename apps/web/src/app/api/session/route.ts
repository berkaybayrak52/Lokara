import { NextResponse } from 'next/server';
import { z } from 'zod';

/**
 * Mints/renews the HttpOnly session cookie — the only place the JWT is ever
 * handled server-side on the web. The browser never reads the token.
 *
 * TODO(supabase): at M5 this becomes the Supabase session exchange (login /
 * refresh-token flow). Until then it proxies the API's dev-token endpoint,
 * which is itself gated by AUTH_DEV_TOKEN and disabled in production.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

const DevTokenSchema = z.object({
  accessToken: z.string(),
  expiresInSeconds: z.number().int().positive(),
});

export async function POST(): Promise<NextResponse> {
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
    secure: process.env.NODE_ENV === 'production',
    maxAge: parsed.data.expiresInSeconds,
    path: '/',
  });
  return response;
}
