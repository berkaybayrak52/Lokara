'use client';

import { StatusNote } from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';

import { API_URL, ApiError } from '@/lib/api';

import { BuildingAttention } from './building-attention';
import { BuildingBanner } from './building-banner';
import { BuildingKpis } from './building-kpis';
import { BuildingModules } from './building-modules';
import { BuildingUnitsBox } from './building-units-box';
import { useBuildingDashboard } from './queries';

/**
 * Objektakte (04_Objekt-Dashboard.md): banner, four KPIs, attention, units,
 * module summaries — every number from one server projection with one `asOf`.
 */
export function BuildingDetailPage({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const dashboard = useBuildingDashboard(accountId, buildingId);
  const [exportState, setExportState] = useState<'idle' | 'pending' | 'error'>('idle');

  async function exportPdf() {
    // Guarded rather than debounced: a second click during generation would
    // start a second identical render (OD3).
    if (exportState === 'pending') return;
    setExportState('pending');
    try {
      const response = await fetch(
        `${API_URL}/a/${accountId}/buildings/${buildingId}/overview.pdf`,
        { credentials: 'include' },
      );
      if (!response.ok) throw new Error('export failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener');
      // The tab keeps its own reference; releasing ours avoids leaking the blob.
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setExportState('idle');
    } catch {
      setExportState('error');
    }
  }

  if (dashboard.isPending) {
    return (
      <main className="py-10">
        <div className="flex flex-col gap-6">
          <div
            aria-hidden="true"
            className="h-72 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
          />
          <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
            <div
              aria-hidden="true"
              className="h-56 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
            <div
              aria-hidden="true"
              className="h-56 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
          </div>
        </div>
        <p className="sr-only">Objektakte wird geladen.</p>
      </main>
    );
  }

  if (dashboard.isError) {
    const missing = dashboard.error instanceof ApiError && dashboard.error.status === 404;
    return (
      <main className="py-10">
        <StatusNote kind="danger" label={missing ? 'Objekt nicht gefunden' : 'Objektakte konnte nicht geladen werden'}>
          {missing ? (
            <Link className="underline underline-offset-4" href={`/a/${accountId}/objekte`}>
              Zurück zu Objekte
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => void dashboard.refetch()}
              className="underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              Erneut versuchen
            </button>
          )}
        </StatusNote>
      </main>
    );
  }

  const data = dashboard.data;
  return (
    <main className="py-10">
      <BuildingBanner
        accountId={accountId}
        dashboard={data}
        onExportPdf={() => void exportPdf()}
        exportState={exportState}
      />

      <div className="mb-8 grid gap-6 xl:grid-cols-[2fr_1fr]">
        <section aria-label="Kennzahlen">
          <h2 className="sr-only">Kennzahlen</h2>
          <BuildingKpis kpis={data.kpis} />
        </section>
        <section aria-label="Aufmerksamkeit">
          <h2 className="sr-only">Aufmerksamkeit</h2>
          <BuildingAttention facts={data.facts} factsTotal={data.factsTotal} />
        </section>
      </div>

      <section aria-label="Einheiten" className="mb-8">
        <h2 className="sr-only">Einheiten</h2>
        <BuildingUnitsBox accountId={accountId} dashboard={data} />
      </section>

      <section aria-label="Fachbereiche">
        <h2 className="sr-only">Fachbereiche</h2>
        <BuildingModules modules={data.modules} />
      </section>

      <p className="mt-6 text-xs text-slate">
        Datenstand: {new Date(data.asOf).toLocaleDateString('de-DE')}
      </p>
    </main>
  );
}
