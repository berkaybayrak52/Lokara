'use client';

import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  StatusNote,
} from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';

import { useBuildingDetail, useBuildings } from '@/features/objekte/queries';

import { HeatingCostSection } from './heating-cost-section';
import { MeterList } from './meter-list';
import { CreateMeterForm } from './create-meter-form';
import { useMeters } from './queries';

/**
 * Zähler (docs/04 M3 page 5) — the last M3 screen.
 *
 * It carries everything the Heizkostenabrechnung stands on: the devices, their
 * Eichfrist, their readings, and the fuel invoice with its CO₂ figures. Those
 * belong together because they are one story — "what did this heating system
 * cost, and who used how much of it" — and because a reading without an
 * invoice bills nothing.
 */
export function MetersPage({ accountId }: { accountId: string }) {
  const buildings = useBuildings(accountId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const buildingId = selectedId ?? buildings.data?.buildings[0]?.id ?? null;

  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Zähler</h1>
        <p className="mt-2 max-w-prose text-slate">
          Zähler je Objekt und Einheit mit Eichfrist, dazu die Ablesungen für den
          Abrechnungszeitraum. Ablesungen werden nur ergänzt, nie überschrieben — eine Korrektur ist
          ein neuer Eintrag, der den alten ablöst.
        </p>
      </header>

      {buildings.isPending ? (
        <div aria-hidden="true" className="h-64 max-w-5xl animate-pulse rounded-xl bg-mint/60" />
      ) : buildings.isError ? (
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          Bitte API und Datenbank prüfen, dann neu laden.
        </StatusNote>
      ) : buildings.data.buildings.length === 0 ? (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Noch kein Objekt</CardTitle>
            <CardDescription>
              Zähler hängen an einem Objekt. Legen Sie zuerst unter{' '}
              <Link
                href={`/a/${accountId}/objekte`}
                className="text-green underline underline-offset-4"
              >
                Objekte
              </Link>{' '}
              ein Gebäude an.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          {buildings.data.buildings.length > 1 ? (
            <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Objekt wählen">
              {buildings.data.buildings.map((b) => {
                const active = b.id === buildingId;
                return (
                  <Button
                    key={b.id}
                    variant={active ? 'default' : 'outline'}
                    size="sm"
                    aria-pressed={active}
                    onClick={() => setSelectedId(b.id)}
                  >
                    {b.name}
                  </Button>
                );
              })}
            </div>
          ) : null}
          {buildingId ? <MetersForBuilding accountId={accountId} buildingId={buildingId} /> : null}
        </>
      )}
    </main>
  );
}

function MetersForBuilding({ accountId, buildingId }: { accountId: string; buildingId: string }) {
  const meters = useMeters(accountId, buildingId);
  const detail = useBuildingDetail(accountId, buildingId);
  const units = (detail.data?.units ?? []).map((u) => ({ id: u.id, label: u.label }));

  const expired = (meters.data?.meters ?? []).filter((m) => m.calibrationStatus === 'EXPIRED');
  const expiringSoon = (meters.data?.meters ?? []).filter(
    (m) => m.calibrationStatus === 'EXPIRING_SOON',
  );

  return (
    <div className="max-w-6xl space-y-8">
      <HeatingCostSection accountId={accountId} buildingId={buildingId} />

      {/* The Eichfrist guard: computed from the meters on every load, so it can
          never go stale. One summary at the top, plus the per-row badge. */}
      {expired.length > 0 ? (
        <StatusNote
          kind="danger"
          label={`${expired.length === 1 ? 'Ein Zähler ist' : `${expired.length} Zähler sind`} nicht mehr geeicht.`}
        >
          Werte nicht geeichter Zähler sind im Streitfall angreifbar (§ 33 MessEG). Betroffen:{' '}
          {expired.map((m) => m.serial).join(', ')}.
        </StatusNote>
      ) : null}
      {expiringSoon.length > 0 ? (
        <StatusNote kind="warning" label="Eichfrist läuft bald ab.">
          Austausch einplanen: {expiringSoon.map((m) => m.serial).join(', ')}.
        </StatusNote>
      ) : null}

      <div className="grid gap-8 lg:grid-cols-[3fr_2fr]">
        <section aria-label="Zähler und Ablesungen">
          {meters.isPending ? (
            <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-mint/60" />
          ) : meters.isError ? (
            <StatusNote kind="danger" label="Zähler konnten nicht geladen werden.">
              Bitte erneut versuchen.
            </StatusNote>
          ) : meters.data.meters.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Zähler erfasst</CardTitle>
                <CardDescription>
                  Für eine Heizkostenabrechnung braucht das Gebäude mindestens einen
                  Wärmemengenzähler (kWh) sowie je Einheit einen Heizkostenverteiler.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <MeterList
              accountId={accountId}
              buildingId={buildingId}
              meters={meters.data.meters}
              periodLabel={meters.data.periodLabel}
            />
          )}
        </section>

        <CreateMeterForm accountId={accountId} buildingId={buildingId} units={units} />
      </div>
    </div>
  );
}
