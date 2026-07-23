import type { CanActivate, ExecutionContext } from '@nestjs/common';
import { Injectable, UnauthorizedException } from '@nestjs/common';
import type { Reflector } from '@nestjs/core';
import jwt from 'jsonwebtoken';
import { IS_PUBLIC_KEY } from './public.decorator';
import type { AuthContext } from './auth.types';

/**
 * Verifies Supabase access tokens (HS256, signed with the project JWT secret).
 *
 * TODO(supabase): with a real project, the `account_id` claim does not exist —
 * at M5 the guard resolves Person → Membership → Account from the URL context
 * (/a/{accountId}/…) and verifies the caller holds that relationship. Until
 * then tokens carry an explicit account_id claim (see dev-token endpoint).
 */
@Injectable()
export class SupabaseJwtGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly jwtSecret: string,
  ) {}

  canActivate(context: ExecutionContext): boolean {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) return true;

    const request = context.switchToHttp().getRequest();
    const header: string | undefined = request.headers['authorization'];
    const token = header?.startsWith('Bearer ') ? header.slice('Bearer '.length) : undefined;
    if (!token) {
      throw new UnauthorizedException('Missing bearer token');
    }

    request.auth = verifySupabaseToken(token, this.jwtSecret);
    return true;
  }
}

export function verifySupabaseToken(token: string, secret: string): AuthContext {
  let payload: jwt.JwtPayload;
  try {
    payload = jwt.verify(token, secret, { algorithms: ['HS256'] }) as jwt.JwtPayload;
  } catch {
    throw new UnauthorizedException('Invalid or expired token');
  }
  const personId = payload.sub;
  const accountId = payload['account_id'] ?? payload['app_metadata']?.account_id;
  if (typeof personId !== 'string' || typeof accountId !== 'string' || accountId.length === 0) {
    throw new UnauthorizedException('Token carries no account context');
  }
  return { personId, accountId };
}
