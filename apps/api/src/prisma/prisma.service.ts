import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { Prisma, PrismaClient } from '@lokara/db';

/**
 * The only Prisma entry point in the codebase (apps/web never touches the DB).
 *
 * Every domain query runs through withAccountContext: it opens a transaction,
 * sets `app.account_id` via SET LOCAL (parameterized through set_config), and
 * runs the callback inside that transaction — so the Postgres RLS policies
 * (packages/db migration) bind to exactly this request's account. This is the
 * second half of the double isolation enforcement (app logic + RLS).
 */
@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  async onModuleInit(): Promise<void> {
    await this.$connect();
  }

  async onModuleDestroy(): Promise<void> {
    await this.$disconnect();
  }

  async withAccountContext<T>(
    accountId: string,
    fn: (tx: Prisma.TransactionClient) => Promise<T>,
  ): Promise<T> {
    return this.$transaction(async (tx) => {
      await tx.$executeRaw`SELECT set_config('app.account_id', ${accountId}, true)`;
      return fn(tx);
    });
  }
}
