'use client';

import { Button, Card, CardContent, CardHeader, CardTitle, StatusNote } from '@lokara/ui';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';
import type { MeterOut, MeterWorkspaceResponse } from '@/lib/contracts';

import { HeatingCostSection } from './heating-cost-section';
import { MeterList } from './meter-list';
import { useMeterWorkspace } from './queries';

export function MetersPage({ accountId }: { accountId: string }) {
  const workspace = useMeterWorkspace(accountId);
  const search = useSearchParams();
  const requestedMeterId = search.get('meterId');
  const [openBuildings, setOpenBuildings] = useState<Set<string>>(new Set());
  const [warningIndex, setWarningIndex] = useState(0);
  const [focusedMeterId, setFocusedMeterId] = useState<string | null>(requestedMeterId);

  const meterPaths = useMemo(() => {
    const paths = new Map<string, { buildingId: string; unitId: string | null }>();
    for (const building of workspace.data?.buildings ?? []) {
      for (const meter of building.buildingMeters) {
        paths.set(meter.id, { buildingId: building.id, unitId: null });
      }
      for (const unit of building.units) {
        for (const meter of unit.meters)
          paths.set(meter.id, { buildingId: building.id, unitId: unit.id });
      }
    }
    return paths;
  }, [workspace.data]);

  useEffect(() => {
    const buildings = workspace.data?.buildings;
    if (!buildings) return;
    if (requestedMeterId && meterPaths.has(requestedMeterId)) {
      setOpenBuildings(new Set([meterPaths.get(requestedMeterId)!.buildingId]));
    } else if (buildings.length === 1) {
      setOpenBuildings(new Set([buildings[0]!.id]));
    }
  }, [meterPaths, requestedMeterId, workspace.data]);

  function focusWarning(index: number) {
    const ids = workspace.data?.expiredMeterIds ?? [];
    if (ids.length === 0) return;
    const normalized = (index + ids.length) % ids.length;
    const meterId = ids[normalized]!;
    const path = meterPaths.get(meterId);
    if (!path) return;
    setWarningIndex(normalized);
    setFocusedMeterId(null);
    setOpenBuildings((current) => new Set(current).add(path.buildingId));
    requestAnimationFrame(() => setFocusedMeterId(meterId));
  }

  const actionBuildingId = openBuildings.size === 1 ? Array.from(openBuildings)[0] : undefined;
  const expiredCount = workspace.data?.expiredMeterIds.length ?? 0;

  return (
    <main className="py-10">
      <PageHeader
        title="Zähler"
        description="Zähler, Ablesungen und Gerätestatus je Objekt und Einheit."
        actions={
          <>
            {expiredCount > 0 ? (
              <Button variant="outline" onClick={() => focusWarning(warningIndex)}>
                Eichfrist von {expiredCount} {expiredCount === 1 ? 'Zähler' : 'Zählern'} abgelaufen
              </Button>
            ) : null}
            {workspace.data?.permissions.canWrite ? (
              <Button asChild>
                <Link
                  href={`/a/${accountId}/zaehler/neu${actionBuildingId ? `?objektId=${actionBuildingId}` : ''}`}
                >
                  Zähler anlegen
                </Link>
              </Button>
            ) : null}
          </>
        }
      />

      {workspace.isPending ? (
        <div
          aria-hidden="true"
          className="h-80 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      ) : workspace.isError ? (
        <StatusNote kind="danger" label="Zählerbestand konnte nicht geladen werden.">
          <button className="underline" onClick={() => void workspace.refetch()}>
            Erneut versuchen
          </button>
        </StatusNote>
      ) : workspace.data.buildings.length === 0 ? (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Noch kein Objekt</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate">Zähler hängen an einem Objekt.</p>
            {workspace.data.permissions.canWrite ? (
              <Link
                className="mt-4 inline-block text-green underline underline-offset-4"
                href={`/a/${accountId}/objekte/neu`}
              >
                Objekt anlegen
              </Link>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <>
          {expiredCount > 1 && focusedMeterId ? (
            <div className="mb-4 flex items-center gap-2 text-sm text-slate">
              <span>
                {warningIndex + 1} von {expiredCount}
              </span>
              <Button variant="ghost" size="sm" onClick={() => focusWarning(warningIndex - 1)}>
                Vorheriger
              </Button>
              <Button variant="ghost" size="sm" onClick={() => focusWarning(warningIndex + 1)}>
                Nächster
              </Button>
            </div>
          ) : null}
          <section aria-label="Zählerbestand" className="space-y-4">
            {workspace.data.buildings.map((building) => (
              <BuildingInventory
                key={building.id}
                accountId={accountId}
                building={building}
                periodLabel={workspace.data.periodLabel}
                canWrite={workspace.data.permissions.canWrite}
                open={openBuildings.has(building.id)}
                onToggle={() =>
                  setOpenBuildings((current) => {
                    const next = new Set(current);
                    if (next.has(building.id)) next.delete(building.id);
                    else next.add(building.id);
                    return next;
                  })
                }
                focusedMeterId={focusedMeterId}
                requestedUnitId={
                  focusedMeterId && meterPaths.get(focusedMeterId)?.buildingId === building.id
                    ? (meterPaths.get(focusedMeterId)?.unitId ?? null)
                    : null
                }
              />
            ))}
          </section>

          <section aria-labelledby="heating-foundations" className="mt-10 space-y-4">
            <div>
              <h2 id="heating-foundations" className="font-display text-2xl font-bold text-ink">
                Heizkosten-Abrechnungsgrundlagen
              </h2>
              <p className="mt-1 text-sm text-slate">
                Interne Eingaben oder Messdienstleister je Objekt und Zeitraum.
              </p>
            </div>
            {workspace.data.buildings.map((building) => (
              <details
                key={building.id}
                className="rounded-xl border border-mint bg-paper"
                open={workspace.data.buildings.length === 1}
              >
                <summary className="cursor-pointer px-5 py-4 font-display font-bold text-ink focus-visible:ring-2 focus-visible:ring-green">
                  {building.name}
                </summary>
                <div className="border-t border-mint p-5">
                  <HeatingCostSection
                    accountId={accountId}
                    buildingId={building.id}
                    units={building.units}
                    canWrite={workspace.data.permissions.canWrite}
                  />
                </div>
              </details>
            ))}
          </section>
        </>
      )}
    </main>
  );
}

type WorkspaceBuilding = MeterWorkspaceResponse['buildings'][number];

function BuildingInventory({
  accountId,
  building,
  periodLabel,
  canWrite,
  open,
  onToggle,
  focusedMeterId,
  requestedUnitId,
}: {
  accountId: string;
  building: WorkspaceBuilding;
  periodLabel: string;
  canWrite: boolean;
  open: boolean;
  onToggle: () => void;
  focusedMeterId: string | null;
  requestedUnitId: string | null;
}) {
  const buildingWarnings = [
    building.expiredCount ? `${building.expiredCount} Eichfrist abgelaufen` : null,
    building.missingDataCount ? `${building.missingDataCount} Eichdaten offen` : null,
  ].filter(Boolean);
  return (
    <article className="rounded-xl border border-mint bg-paper">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left outline-none hover:bg-mint/30 focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-inset"
        aria-expanded={open}
        aria-controls={`building-meters-${building.id}`}
        onClick={onToggle}
      >
        <span>
          <span className="font-display text-lg font-bold text-ink">{building.name}</span>
          <span className="mt-1 block text-sm text-slate">
            {building.address} · {building.activeMeterCount} aktive Zähler
            {buildingWarnings.length ? ` · ${buildingWarnings.join(' · ')}` : ''}
          </span>
        </span>
        <span aria-hidden="true" className="text-xl text-slate">
          {open ? '−' : '+'}
        </span>
      </button>
      <div id={`building-meters-${building.id}`} hidden={!open}>
        {open ? (
          <div className="space-y-4 border-t border-mint p-4 sm:p-5">
            <MeterGroup
              title="Gebäudezähler"
              empty="Noch kein Gebäudezähler erfasst."
              meters={building.buildingMeters}
              accountId={accountId}
              buildingId={building.id}
              periodLabel={periodLabel}
              canWrite={canWrite}
              focusedMeterId={focusedMeterId}
              emptyActionHref={
                canWrite ? `/a/${accountId}/zaehler/neu?objektId=${building.id}` : undefined
              }
            />
            {building.units.map((unit) => (
              <UnitInventory
                key={unit.id}
                accountId={accountId}
                buildingId={building.id}
                unit={unit}
                periodLabel={periodLabel}
                canWrite={canWrite}
                focusMeterId={focusedMeterId}
                initialOpen={requestedUnitId === unit.id}
              />
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function UnitInventory({
  accountId,
  buildingId,
  unit,
  periodLabel,
  canWrite,
  focusMeterId,
  initialOpen,
}: {
  accountId: string;
  buildingId: string;
  unit: WorkspaceBuilding['units'][number];
  periodLabel: string;
  canWrite: boolean;
  focusMeterId: string | null;
  initialOpen: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  useEffect(() => {
    if (initialOpen) setOpen(true);
  }, [initialOpen]);
  return (
    <section className="rounded-xl border border-mint">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left outline-none hover:bg-mint/30 focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-inset"
        aria-expanded={open}
        aria-controls={`unit-meters-${unit.id}`}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="font-semibold text-ink">
          {unit.label}
          <span className="ml-2 text-sm font-normal text-slate">
            {unit.activeMeterCount} aktive Zähler
            {unit.warningCount ? ` · ${unit.warningCount} Status offen` : ''}
          </span>
        </span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      <div id={`unit-meters-${unit.id}`} hidden={!open}>
        {open ? (
          <div className="border-t border-mint p-3">
            <MeterGroup
              title="Aktive und historische Zähler"
              empty="Dieser Einheit ist noch kein Zähler zugeordnet."
              meters={unit.meters}
              accountId={accountId}
              buildingId={buildingId}
              periodLabel={periodLabel}
              canWrite={canWrite}
              focusedMeterId={focusMeterId}
              emptyActionHref={
                canWrite
                  ? `/a/${accountId}/zaehler/neu?objektId=${buildingId}&einheitId=${unit.id}`
                  : undefined
              }
            />
          </div>
        ) : null}
      </div>
    </section>
  );
}

function MeterGroup({
  title,
  empty,
  meters,
  accountId,
  buildingId,
  periodLabel,
  canWrite,
  focusedMeterId,
  emptyActionHref,
}: {
  title: string;
  empty: string;
  meters: MeterOut[];
  accountId: string;
  buildingId: string;
  periodLabel: string;
  canWrite: boolean;
  focusedMeterId: string | null;
  emptyActionHref?: string;
}) {
  const active = meters.filter((meter) => meter.lifecycleStatus === 'ACTIVE');
  const historical = meters.filter((meter) => meter.lifecycleStatus !== 'ACTIVE');
  return (
    <div className="space-y-3">
      <h3 className="font-display text-sm font-bold text-ink">{title}</h3>
      {meters.length === 0 ? (
        <div className="rounded-lg bg-mint/30 p-4 text-sm text-slate">
          <p>{empty}</p>
          {emptyActionHref ? (
            <Link
              className="mt-2 inline-block font-semibold text-green underline underline-offset-4"
              href={emptyActionHref}
            >
              Zähler anlegen
            </Link>
          ) : null}
        </div>
      ) : null}
      {active.length ? (
        <MeterList
          accountId={accountId}
          buildingId={buildingId}
          meters={active}
          periodLabel={periodLabel}
          canWrite={canWrite}
          focusMeterId={focusedMeterId}
        />
      ) : null}
      {historical.length ? (
        <details className="rounded-lg border border-mint">
          <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-ink">
            Historische Zähler ({historical.length})
          </summary>
          <div className="border-t border-mint">
            <MeterList
              accountId={accountId}
              buildingId={buildingId}
              meters={historical}
              periodLabel={periodLabel}
              canWrite={false}
              focusMeterId={focusedMeterId}
            />
          </div>
        </details>
      ) : null}
    </div>
  );
}
