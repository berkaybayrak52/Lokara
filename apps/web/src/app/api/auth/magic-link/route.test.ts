import { beforeEach, describe, expect, it, vi } from 'vitest';

const signInWithOtp = vi.fn();

vi.mock('@/lib/supabase-auth', () => ({
  createSupabaseAuthClient: () => ({ auth: { signInWithOtp } }),
}));

import { POST } from './route';

describe('invite-only magic-link route', () => {
  beforeEach(() => signInWithOtp.mockReset());

  it('never permits the magic-link call to create a user', async () => {
    signInWithOtp.mockResolvedValue({ error: null });
    const response = await POST(
      new Request('https://lokara.example/api/auth/magic-link', {
        body: JSON.stringify({ email: 'eingeladen@example.de' }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      }),
    );

    expect(response.status).toBe(200);
    expect(signInWithOtp).toHaveBeenCalledWith({
      email: 'eingeladen@example.de',
      options: {
        emailRedirectTo: 'https://lokara.example/auth/confirm',
        shouldCreateUser: false,
      },
    });
  });

  it('does not reveal whether an address was invited', async () => {
    signInWithOtp.mockResolvedValue({ error: { status: 400 } });
    const response = await POST(
      new Request('https://lokara.example/api/auth/magic-link', {
        body: JSON.stringify({ email: 'unbekannt@example.de' }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      }),
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it('rejects malformed email input before calling Supabase', async () => {
    const response = await POST(
      new Request('https://lokara.example/api/auth/magic-link', {
        body: JSON.stringify({ email: 'keine-adresse' }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      }),
    );

    expect(response.status).toBe(400);
    expect(signInWithOtp).not.toHaveBeenCalled();
  });
});
