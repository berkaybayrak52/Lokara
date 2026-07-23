import { Module } from '@nestjs/common';
import { APP_GUARD, Reflector } from '@nestjs/core';
import { DevTokenController } from './auth/dev-token.controller';
import { SupabaseJwtGuard } from './auth/supabase-jwt.guard';
import { DemoController } from './demo/demo.controller';
import { HealthController } from './health/health.controller';
import { PrismaService } from './prisma/prisma.service';
import { loadEnv } from './env';

@Module({
  controllers: [HealthController, DevTokenController, DemoController],
  providers: [
    PrismaService,
    {
      provide: APP_GUARD,
      useFactory: (reflector: Reflector) =>
        new SupabaseJwtGuard(reflector, loadEnv().supabaseJwtSecret),
      inject: [Reflector],
    },
  ],
})
export class AppModule {}
