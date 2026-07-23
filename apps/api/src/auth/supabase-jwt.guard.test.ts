import { describe, expect, it } from 'vitest';
import jwt from 'jsonwebtoken';
import { UnauthorizedException } from '@nestjs/common';
import { verifySupabaseToken } from './supabase-jwt.guard';

const SECRET = 'test-secret-that-is-long-enough!!';

describe('verifySupabaseToken', () => {
  it('accepts a valid HS256 token and extracts person + account', () => {
    const token = jwt.sign({ sub: 'per_1', account_id: 'acc_1' }, SECRET, {
      algorithm: 'HS256',
      expiresIn: 60,
    });
    expect(verifySupabaseToken(token, SECRET)).toEqual({ personId: 'per_1', accountId: 'acc_1' });
  });

  it('rejects a token signed with another secret', () => {
    const token = jwt.sign({ sub: 'per_1', account_id: 'acc_1' }, 'wrong-secret-wrong-secret', {
      algorithm: 'HS256',
    });
    expect(() => verifySupabaseToken(token, SECRET)).toThrow(UnauthorizedException);
  });

  it('rejects an expired token', () => {
    const token = jwt.sign({ sub: 'per_1', account_id: 'acc_1' }, SECRET, {
      algorithm: 'HS256',
      expiresIn: -10,
    });
    expect(() => verifySupabaseToken(token, SECRET)).toThrow(UnauthorizedException);
  });

  it('rejects tokens without an account context', () => {
    const token = jwt.sign({ sub: 'per_1' }, SECRET, { algorithm: 'HS256' });
    expect(() => verifySupabaseToken(token, SECRET)).toThrow(UnauthorizedException);
  });

  it('accepts account_id from app_metadata (Supabase custom claims shape)', () => {
    const token = jwt.sign({ sub: 'per_1', app_metadata: { account_id: 'acc_2' } }, SECRET, {
      algorithm: 'HS256',
    });
    expect(verifySupabaseToken(token, SECRET).accountId).toBe('acc_2');
  });
});
