import { Controller, ForbiddenException, Post } from '@nestjs/common';
import jwt from 'jsonwebtoken';
import { Public } from './public.decorator';
import { loadEnv } from '../env';
import type { DevTokenResponse } from '../contract';

const EXPIRES_IN_SECONDS = 60 * 60;

/**
 * DEV ONLY — issues a token shaped like a Supabase access token so the guard
 * path is exercisable without a Supabase project. Disabled unless
 * AUTH_DEV_TOKEN=true, and never in production. TODO(supabase): delete once
 * real Supabase Auth is wired (M5).
 */
@Controller('auth')
export class DevTokenController {
  @Public()
  @Post('dev-token')
  issue(): DevTokenResponse {
    const env = loadEnv();
    if (!env.devTokenEnabled) {
      throw new ForbiddenException('Dev tokens are disabled');
    }
    const accessToken = jwt.sign(
      {
        sub: 'per_demo_owner',
        account_id: 'acc_demo_lokara',
        role: 'authenticated',
      },
      env.supabaseJwtSecret,
      { algorithm: 'HS256', expiresIn: EXPIRES_IN_SECONDS },
    );
    return { accessToken, expiresInSeconds: EXPIRES_IN_SECONDS };
  }
}
