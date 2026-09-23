import type { EmailOtpType } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import { z } from 'zod';

import { createSupabaseAuthClient, setSessionCookies } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

const ConfirmationSchema = z.object({
  token_hash: z.string().min(1).max(1024),
  type: z.enum(['invite', 'magiclink']),
});

export async function GET(request: Request): Promise<NextResponse> {
  const url = new URL(request.url);
  const confirmation = ConfirmationSchema.safeParse({
    token_hash: url.searchParams.get('token_hash'),
    type: url.searchParams.get('type'),
  });
  if (!confirmation.success) {
    return NextResponse.redirect(new URL('/login?error=invalid_link', url.origin), 303);
  }

  let supabase: ReturnType<typeof createSupabaseAuthClient>;
  try {
    supabase = createSupabaseAuthClient();
  } catch {
    return NextResponse.redirect(new URL('/login?error=auth_unavailable', url.origin), 303);
  }

  const { data, error } = await supabase.auth.verifyOtp({
    token_hash: confirmation.data.token_hash,
    type: confirmation.data.type as EmailOtpType,
  });
  if (error || !data.session) {
    return NextResponse.redirect(new URL('/login?error=invalid_link', url.origin), 303);
  }

  const response = NextResponse.redirect(new URL('/', url.origin), 303);
  setSessionCookies(response, data.session);
  return response;
}
