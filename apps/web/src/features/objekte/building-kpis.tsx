'use client';

import { Card, CardContent } from '@lokara/ui';

import type { BuildingDashboardResponse } from '@/lib/contracts';

function Kpi({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card className="border-l-4 border-l-green">
      <CardContent className="pt-6">
        <p className="text-sm text-slate">{label}</p>
        <p className="mt-1 font-display text-2xl font-semibold tabular-nums break-words text-ink">
          {value}
        </p>
        <p className="mt-1 text-xs text-slate">{hint}</p>
      </CardContent>
    </Card>
  );
}

/**
 * The four object KPIs (OD4). Every value arrives finished from the server —
 * this component performs no division, no summation and no formatting of money.
 */
export function BuildingKpis({ kpis }: { kpis: BuildingDashboardResponse['kpis'] }) {
  const occupancy = kpis.occupancy;
  const occupancyDetails = [
    occupancy.vacant > 0 ? `${occupancy.vacant} Leerstand` : null,
    occupancy.selfUse > 0 ? `${occupancy.selfUse} Eigennutzung` : null,
  ].filter((part): part is string => part !== null);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Kpi
        label="Kaltmiete / Monat"
        value={kpis.coldRentEurMonthly}
        hint="Kaltmiete ohne Vorauszahlungen"
      />
      <Kpi
        label="Gesamtfläche"
        value={`${kpis.totalAreaSqm.toLocaleString('de-DE')} m²`}
        hint="Summe der erfassten Einheitenflächen"
      />
      <Kpi
        label="Ø Kaltmiete / m²"
        value={kpis.avgColdRentEurPerSqm ?? '–'}
        hint={
          kpis.avgColdRentEurPerSqm === null
            ? 'Noch keine vermietete Fläche'
            : 'Gewichtet: Kaltmiete geteilt durch vermietete Fläche'
        }
      />
      <Kpi
        label="Vermietungsstand"
        value={`${occupancy.rented} von ${occupancy.total} vermietet`}
        hint={occupancyDetails.length > 0 ? occupancyDetails.join(' · ') : 'Vollständig vermietet'}
      />
    </div>
  );
}
