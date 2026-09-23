import { createClient, type Session } from '@supabase/supabase-js';
import type { NextResponse } from 'next/server';

export const ACCESS_TOKEN_COOKIE = 'lokara_access_token';
export const REFRESH_TOKEN_COOKIE = 'lokara_refresh_token';

const REFRESH_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export function createSupabaseAuthClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !publishableKey) {
    throw new Error('Supabase Auth is not configured');
  }

  return createClient(url, publishableKey, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false,
    },
  });
}

export function setSessionCookies(response: NextResponse, session: Session): void {
  const secure = process.env.NODE_ENV === 'production';
  response.cookies.set(ACCESS_TOKEN_COOKIE, session.access_token, {
    httpOnly: true,
    maxAge: session.expires_in,
    path: '/',
    sameSite: 'lax',
    secure,
  });
  response.cookies.set(REFRESH_TOKEN_COOKIE, session.refresh_token, {
    httpOnly: true,
    maxAge: REFRESH_COOKIE_MAX_AGE_SECONDS,
    // The refresh credential is never sent to FastAPI through /api/backend.
    path: '/api/session',
    sameSite: 'lax',
    secure,
  });
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.set(ACCESS_TOKEN_COOKIE, '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  });
  response.cookies.set(REFRESH_TOKEN_COOKIE, '', {
    httpOnly: true,
    maxAge: 0,
    path: '/api/session',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  });
}
