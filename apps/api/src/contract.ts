/**
 * The typed HTTP contract between apps/api and its clients (apps/web today,
 * native iOS/Android at launch). Plain types only — importing this file must
 * never pull NestJS or Prisma into a client bundle.
 */

export interface HealthResponse {
  status: 'ok';
  service: 'lokara-api';
  timestamp: string;
}

export interface DevTokenResponse {
  accessToken: string;
  expiresInSeconds: number;
}

export interface DemoTenancySummary {
  unitLabel: string;
  areaSqm: number;
  renterNames: string[];
  validFrom: string;
  validTo: string | null;
  baseRentEur: string;
}

export interface DemoSummaryResponse {
  accountName: string;
  buildingName: string;
  buildingAddress: string;
  unitCount: number;
  tenancies: DemoTenancySummary[];
}
