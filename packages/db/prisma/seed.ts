/**
 * Seeds the demo scenario from lokara-arch.md §10 (the €1,200 garbage-cost example):
 * one building, three units (50/30/20 m²), Renter 2 moves out on 30 Jun 2025.
 * Idempotent (upserts on fixed ids). RLS is FORCEd, so the session must present
 * the account context before touching domain rows — exactly like the API does.
 */
import { PrismaClient } from '../generated/client';

export const DEMO_ACCOUNT_ID = 'acc_demo_lokara';
export const DEMO_PERSON_ID = 'per_demo_owner';

const prisma = new PrismaClient();

async function main(): Promise<void> {
  // Person + Account carry no accountId column and are not RLS-scoped.
  await prisma.person.upsert({
    where: { id: DEMO_PERSON_ID },
    update: {},
    create: { id: DEMO_PERSON_ID, email: 'demo@lokara.example', name: 'Demo Vermieter' },
  });
  await prisma.account.upsert({
    where: { id: DEMO_ACCOUNT_ID },
    update: {},
    create: { id: DEMO_ACCOUNT_ID, name: 'Demo Konto', shape: 'SOLO' },
  });

  // Domain rows are behind FORCEd RLS — set the account context for this session.
  await prisma.$executeRawUnsafe(`SET app.account_id = '${DEMO_ACCOUNT_ID}'`);

  await prisma.building.upsert({
    where: { id: 'bld_demo_muster12' },
    update: {},
    create: {
      id: 'bld_demo_muster12',
      accountId: DEMO_ACCOUNT_ID,
      name: 'Musterstraße 12',
      street: 'Musterstraße 12',
      postalCode: '60311',
      city: 'Frankfurt am Main',
    },
  });

  const units = [
    { id: 'unit_demo_a', label: 'Wohnung A (EG links)', areaSqmX100: 5000 },
    { id: 'unit_demo_b', label: 'Wohnung B (EG rechts)', areaSqmX100: 3000 },
    { id: 'unit_demo_c', label: 'Wohnung C (1. OG)', areaSqmX100: 2000 },
  ];
  for (const u of units) {
    await prisma.unit.upsert({
      where: { id: u.id },
      update: {},
      create: { ...u, accountId: DEMO_ACCOUNT_ID, buildingId: 'bld_demo_muster12' },
    });
  }

  const renters = [
    { id: 'ren_demo_1', legalName: 'Anna Beispiel' },
    { id: 'ren_demo_2', legalName: 'Bernd Muster' },
    { id: 'ren_demo_3', legalName: 'Clara Vorlage' },
  ];
  for (const r of renters) {
    await prisma.renter.upsert({
      where: { id: r.id },
      update: {},
      create: { ...r, accountId: DEMO_ACCOUNT_ID },
    });
  }

  const tenancies = [
    // Renter 1: Unit A, whole 2025, still running.
    {
      id: 'ten_demo_a1',
      unitId: 'unit_demo_a',
      renterId: 'ren_demo_1',
      validFrom: '2023-04-01',
      validTo: null,
      baseRentCents: 95000,
      advancePaymentCents: 22000,
    },
    // Renter 2: Unit B, moves out 30 Jun 2025 (validTo exclusive → 2025-07-01).
    {
      id: 'ten_demo_b1',
      unitId: 'unit_demo_b',
      renterId: 'ren_demo_2',
      validFrom: '2021-09-01',
      validTo: '2025-07-01',
      baseRentCents: 68000,
      advancePaymentCents: 15000,
    },
    // Renter 3: Unit C, whole 2025, still running.
    {
      id: 'ten_demo_c1',
      unitId: 'unit_demo_c',
      renterId: 'ren_demo_3',
      validFrom: '2024-01-01',
      validTo: null,
      baseRentCents: 52000,
      advancePaymentCents: 11000,
    },
  ];
  for (const t of tenancies) {
    await prisma.tenancy.upsert({
      where: { id: t.id },
      update: {},
      create: {
        id: t.id,
        accountId: DEMO_ACCOUNT_ID,
        unitId: t.unitId,
        validFrom: new Date(`${t.validFrom}T00:00:00.000Z`),
        validTo: t.validTo ? new Date(`${t.validTo}T00:00:00.000Z`) : null,
        baseRentCents: t.baseRentCents,
        advancePaymentCents: t.advancePaymentCents,
      },
    });
    await prisma.tenancyParty.upsert({
      where: { tenancyId_renterId: { tenancyId: t.id, renterId: t.renterId } },
      update: {},
      create: { accountId: DEMO_ACCOUNT_ID, tenancyId: t.id, renterId: t.renterId },
    });
  }

  console.log('Seed complete: demo account, building Musterstraße 12, 3 units, 3 tenancies.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
