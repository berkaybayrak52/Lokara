import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'isPublic';

/** Marks an endpoint as reachable without a Supabase JWT (e.g. /health). */
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
