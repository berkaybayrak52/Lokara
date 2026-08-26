'use client';

import { Button } from '@lokara/ui';
import Link from 'next/link';

import type { BuildingDashboardResponse } from '@/lib/contracts';

/**
 * Objektakte header (OD2/OD3): identity first, then the two object actions.
 *
 * The picture area is a calm placeholder, not an uploader — the app has no
 * object storage yet, and a dropzone that silently discards a file is worse
 * than an honest "kommt bald".
 */
export function BuildingBanner({
  accountId,
  dashboard,
  onExportPdf,
  exportState,
}: {
  accountId: string;
  dashboard: BuildingDashboardResponse;
  onExportPdf: () => void;
  exportState: 'idle' | 'pending' | 'error';
}) {
  const unitLabel = dashboard.unitCount === 1 ? '1 Einheit' : `${dashboard.unitCount} Einheiten`;

  return (
    <section aria-label="Objektübersicht" className="mb-8 overflow-hidden rounded-xl border border-mint">
      <div
        aria-hidden="true"
        className="flex h-[220px] items-center justify-center bg-mint/60 text-slate"
      >
        <span className="text-sm">Objektfoto hinzufügen · Foto-Upload kommt bald</span>
      </div>
      <div className="flex flex-wrap items-start justify-between gap-4 bg-paper p-6">
        <div className="min-w-0">
          <p className="mb-1 text-sm">
            <Link
              href={`/a/${accountId}/objekte`}
              className="text-green underline-offset-4 hover:underline"
            >
              Objekte
            </Link>
          </p>
          <h1 className="font-display text-2xl font-semibold break-words text-ink">
            {dashboard.name}
          </h1>
          <p className="mt-1 break-words text-slate">
            {dashboard.street}, {dashboard.postalCode} {dashboard.city}
          </p>
          <p className="mt-1 text-sm text-slate">
            {dashboard.buildingTypeLabel} ·{' '}
            {dashboard.isResidential ? 'Wohngebäude' : 'Nichtwohngebäude'} · {unitLabel}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/*
            "Objekt bearbeiten" (OD3) is deliberately absent: the API has no
            building update route and 02_Objekte shipped only the creation
            wizards, so the action would be a link to a 404. A visible control
            that cannot do its job is the fake function this spec forbids.
          */}
          {dashboard.permissions.canExportPdf ? (
            <Button variant="secondary" onClick={onExportPdf} disabled={exportState === 'pending'}>
              {exportState === 'pending' ? 'PDF wird erstellt…' : 'Objektübersicht als PDF'}
            </Button>
          ) : null}
        </div>
        {exportState === 'error' ? (
          <p role="status" className="w-full text-sm text-danger">
            PDF konnte nicht erstellt werden. Bitte erneut versuchen.
          </p>
        ) : null}
      </div>
    </section>
  );
}
