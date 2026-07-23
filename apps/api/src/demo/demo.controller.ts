import { Controller, Get, Inject, NotFoundException, Req } from '@nestjs/common';
import { formatEur, cents } from '@lokara/domain';
import { PrismaService } from '../prisma/prisma.service';
import type { AuthenticatedRequest } from '../auth/auth.types';
import type { DemoSummaryResponse } from '../contract';

/**
 * Guarded demo endpoint proving the M0 spine: JWT guard → account context →
 * RLS-scoped Prisma queries → typed contract response consumed by apps/web.
 */
@Controller('demo')
export class DemoController {
  // Explicit @Inject: the dev runner (tsx/esbuild) emits no decorator metadata,
  // so type-based constructor injection cannot resolve.
  constructor(@Inject(PrismaService) private readonly prisma: PrismaService) {}

  @Get('summary')
  async summary(@Req() req: AuthenticatedRequest): Promise<DemoSummaryResponse> {
    const auth = req.auth;
    if (!auth) throw new NotFoundException(); // unreachable behind the guard

    return this.prisma.withAccountContext(auth.accountId, async (tx) => {
      const account = await tx.account.findUnique({ where: { id: auth.accountId } });
      const building = await tx.building.findFirst({
        where: { accountId: auth.accountId },
        include: {
          units: {
            include: {
              tenancies: { include: { parties: { include: { renter: true } } } },
            },
            orderBy: { label: 'asc' },
          },
        },
      });
      if (!account || !building) {
        throw new NotFoundException('No demo data — run `pnpm db:seed` first.');
      }

      return {
        accountName: account.name,
        buildingName: building.name,
        buildingAddress: `${building.street}, ${building.postalCode} ${building.city}`,
        unitCount: building.units.length,
        tenancies: building.units.flatMap((unit) =>
          unit.tenancies.map((t) => ({
            unitLabel: unit.label,
            areaSqm: unit.areaSqmX100 / 100,
            renterNames: t.parties.map((p) => p.renter.legalName),
            validFrom: t.validFrom.toISOString().slice(0, 10),
            validTo: t.validTo ? t.validTo.toISOString().slice(0, 10) : null,
            baseRentEur: formatEur(cents(t.baseRentCents)),
          })),
        ),
      };
    });
  }
}
