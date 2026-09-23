import { NextResponse } from 'next/server';
import { z } from 'zod';

import { createSupabaseAuthClient } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

const RequestSchema = z.object({
  email: z.string().trim().email().max(254),
});

export async function POST(request: Request): Promise<NextResponse> {
  const input = RequestSchema.safeParse(await request.json().catch(() => null));
  if (!input.success) {
    return NextResponse.json({ error: 'invalid_email' }, { status: 400 });
  }

  let supabase: ReturnType<typeof createSupabaseAuthClient>;
  try {
    supabase = createSupabaseAuthClient();
  } catch {
    return NextResponse.json({ error: 'auth_unavailable' }, { status: 503 });
  }

  const redirectTo = new URL('/auth/confirm', request.url).toString();
  const { error } = await supabase.auth.signInWithOtp({
    email: input.data.email,
    options: {
      emailRedirectTo: redirectTo,
      shouldCreateUser: false,
    },
  });

  if (error?.status === 429) {
    return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
  }
  if (error && (error.status ?? 500) >= 500) {
    return NextResponse.json({ error: 'auth_unavailable' }, { status: 502 });
  }

  // Existing and unknown addresses deliberately receive the same response.
  return NextResponse.json({ ok: true } as const);
}
