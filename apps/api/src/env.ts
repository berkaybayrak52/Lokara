import path from 'node:path';
import dotenv from 'dotenv';

// Root .env first (shared), then a local apps/api/.env may override.
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env'), override: true });

export interface ApiEnv {
  readonly port: number;
  readonly webOrigin: string;
  readonly supabaseJwtSecret: string;
  readonly devTokenEnabled: boolean;
}

export function loadEnv(): ApiEnv {
  const secret = process.env.SUPABASE_JWT_SECRET;
  if (!secret || secret.length < 16) {
    throw new Error('SUPABASE_JWT_SECRET must be set (>=16 chars). See .env.example.');
  }
  const devTokenEnabled =
    process.env.AUTH_DEV_TOKEN === 'true' && process.env.NODE_ENV !== 'production';
  return {
    port: Number(process.env.API_PORT ?? 3001),
    webOrigin: process.env.WEB_ORIGIN ?? 'http://localhost:3000',
    supabaseJwtSecret: secret,
    devTokenEnabled,
  };
}
