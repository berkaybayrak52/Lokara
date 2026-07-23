/**
 * Allocation keys (Umlageschlüssel) — mirrors the Prisma `AllocationKey` enum.
 * The key never lives on a cost row; it lives on a per-period assignment so
 * changing a key re-runs the calculation without deleting entered data.
 */
export const ALLOCATION_KEYS = [
  'AREA', // Fläche (Wohnfläche)
  'PERSONS', // Personen
  'CONSUMPTION', // Verbrauch (metered)
  'UNITS', // Einheiten
  'DIRECT', // Direktzuordnung — cost assigned to exactly one unit/tenancy
  'MEA', // Miteigentumsanteil (WEG)
] as const;

export type AllocationKey = (typeof ALLOCATION_KEYS)[number];
