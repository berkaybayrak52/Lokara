-- CreateEnum
CREATE TYPE "AccountShape" AS ENUM ('SOLO', 'HAUSVERWALTUNG');

-- CreateEnum
CREATE TYPE "StatementStatus" AS ENUM ('DRAFT', 'FINALIZED', 'SUPERSEDED');

-- CreateEnum
CREATE TYPE "AllocationKey" AS ENUM ('AREA', 'PERSONS', 'CONSUMPTION', 'UNITS', 'DIRECT', 'MEA');

-- CreateTable
CREATE TABLE "Person" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Person_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Account" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "shape" "AccountShape" NOT NULL DEFAULT 'SOLO',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Account_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Building" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "street" TEXT NOT NULL,
    "postalCode" TEXT NOT NULL,
    "city" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Building_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Unit" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "buildingId" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "areaSqmX100" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Unit_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Tenancy" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "unitId" TEXT NOT NULL,
    "validFrom" TIMESTAMP(3) NOT NULL,
    "validTo" TIMESTAMP(3),
    "baseRentCents" INTEGER NOT NULL,
    "advancePaymentCents" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Tenancy_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Renter" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "legalName" TEXT NOT NULL,
    "email" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Renter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TenancyParty" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "tenancyId" TEXT NOT NULL,
    "renterId" TEXT NOT NULL,

    CONSTRAINT "TenancyParty_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Statement" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "buildingId" TEXT NOT NULL,
    "periodStart" TIMESTAMP(3) NOT NULL,
    "periodEnd" TIMESTAMP(3) NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "status" "StatementStatus" NOT NULL DEFAULT 'DRAFT',
    "totalCents" INTEGER NOT NULL,
    "contentHash" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Statement_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Person_email_key" ON "Person"("email");

-- CreateIndex
CREATE INDEX "Building_accountId_idx" ON "Building"("accountId");

-- CreateIndex
CREATE INDEX "Unit_accountId_idx" ON "Unit"("accountId");

-- CreateIndex
CREATE INDEX "Unit_buildingId_idx" ON "Unit"("buildingId");

-- CreateIndex
CREATE INDEX "Tenancy_accountId_idx" ON "Tenancy"("accountId");

-- CreateIndex
CREATE INDEX "Tenancy_unitId_idx" ON "Tenancy"("unitId");

-- CreateIndex
CREATE INDEX "Renter_accountId_idx" ON "Renter"("accountId");

-- CreateIndex
CREATE INDEX "TenancyParty_accountId_idx" ON "TenancyParty"("accountId");

-- CreateIndex
CREATE UNIQUE INDEX "TenancyParty_tenancyId_renterId_key" ON "TenancyParty"("tenancyId", "renterId");

-- CreateIndex
CREATE INDEX "Statement_accountId_idx" ON "Statement"("accountId");

-- CreateIndex
CREATE UNIQUE INDEX "Statement_buildingId_periodStart_periodEnd_version_key" ON "Statement"("buildingId", "periodStart", "periodEnd", "version");

-- AddForeignKey
ALTER TABLE "Building" ADD CONSTRAINT "Building_accountId_fkey" FOREIGN KEY ("accountId") REFERENCES "Account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Unit" ADD CONSTRAINT "Unit_buildingId_fkey" FOREIGN KEY ("buildingId") REFERENCES "Building"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Tenancy" ADD CONSTRAINT "Tenancy_unitId_fkey" FOREIGN KEY ("unitId") REFERENCES "Unit"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Renter" ADD CONSTRAINT "Renter_accountId_fkey" FOREIGN KEY ("accountId") REFERENCES "Account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TenancyParty" ADD CONSTRAINT "TenancyParty_tenancyId_fkey" FOREIGN KEY ("tenancyId") REFERENCES "Tenancy"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TenancyParty" ADD CONSTRAINT "TenancyParty_renterId_fkey" FOREIGN KEY ("renterId") REFERENCES "Renter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Statement" ADD CONSTRAINT "Statement_accountId_fkey" FOREIGN KEY ("accountId") REFERENCES "Account"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Statement" ADD CONSTRAINT "Statement_buildingId_fkey" FOREIGN KEY ("buildingId") REFERENCES "Building"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- ── Row-Level Security backstop (CLAUDE.md rule 3) ────────────────────────────
-- Isolation is enforced twice: in app logic AND here. The API sets
-- `app.account_id` per request (SET LOCAL inside a transaction). FORCE makes the
-- policy bind even for the table owner, so a missing context yields zero rows —
-- never someone else's data. Full RLS hardening (roles, portals) lands at M5.

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['Building', 'Unit', 'Tenancy', 'Renter', 'TenancyParty', 'Statement']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY account_isolation ON %I '
      'USING ("accountId" = current_setting(''app.account_id'', true)) '
      'WITH CHECK ("accountId" = current_setting(''app.account_id'', true))',
      t
    );
  END LOOP;
END $$;
