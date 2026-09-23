import type { Session } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import { describe, expect, it } from 'vitest';

import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, setSessionCookies } from './supabase-auth';

describe('Supabase session cookies', () => {
  it('keeps both credentials HttpOnly and limits the refresh token to its route', () => {
    const response = NextResponse.json({ ok: true });
    setSessionCookies(response, {
      access_token: 'access-value',
      expires_at: 1_800_000_000,
      expires_in: 3600,
      refresh_token: 'refresh-value',
      token_type: 'bearer',
      user: { id: 'person-1' },
    } as Session);

    expect(response.cookies.get(ACCESS_TOKEN_COOKIE)).toMatchObject({
      httpOnly: true,
      path: '/',
      sameSite: 'lax',
      value: 'access-value',
    });
    expect(response.cookies.get(REFRESH_TOKEN_COOKIE)).toMatchObject({
      httpOnly: true,
      path: '/api/session',
      sameSite: 'lax',
      value: 'refresh-value',
    });
  });
});
