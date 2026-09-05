'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Select,
  StatusNote,
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { useBuildingDetail, useBuildings } from '@/features/objekte/queries';
import { PageHeader } from '@/features/portal/page-header';
import type { AllocationKey, CostEntryOut } from '@/lib/contracts';
import { ALLOCATION_KEYS, ALLOCATION_KEY_LABELS } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';

import { useCosts, useReassignKey, useVoidCost } from './queries';

const FINDING_LABELS: Record<string, string> = {
  'verify-before-production': 'Vor Produktivnutzung rechtlich prüfen.',
  'nr17-nicht-benannt': 'Als sonstige Betriebskosten im Mietvertrag nicht benannt.',
  'umlagevereinbarung-fehlt': 'Keine Umlagevereinbarung hinterlegt.',
  'mehrbelastungsklausel-fehlt': 'Neue Kostenart ohne Mehrbelastungsklausel.',
  'lohnanteil-vorgeschlagen': 'Lohnanteil geschätzt — bitte prüfen.',
  'trinkwasser-nr17-fallback': 'Ersatzweise als Wasserkosten geführt.',
};

/** Kosten erfassen (docs/04 M3 page 4). */
export function CostsPage({
  accountId,
  initialBuildingId = null,
}: {
  accountId: string;
  initialBuildingId?: string | null;
}) {
  const buildings = useBuildings(accountId);
  const [selectedId, setSelectedId] = useState<string | null>(initialBuildingId);
  const selectedExists = buildings.data?.buildings.some((building) => building.id === selectedId);
  const buildingId =
    selectedExists === true ? selectedId : (buildings.data?.buildings[0]?.id ?? null);

  return (
    <main className="py-10">
      <PageHeader
        title="Kosten erfassen"
        description="Betriebskosten je Objekt und Abrechnungszeitraum. Der Umlageschlüssel wird pro Kostenart gewählt und kann jederzeit geändert werden — die Abrechnung rechnet neu, erfasste Daten bleiben erhalten."
      />

      {buildings.isPending ? (
        <div
          aria-hidden="true"
          className="h-64 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      ) : buildings.isError ? (
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          Laden Sie die Seite neu oder versuchen Sie es später erneut.
        </StatusNote>
      ) : buildings.data.buildings.length === 0 ? (
        <Card className="max-w-xl border-l-4 border-l-green">
          <CardHeader>
            <CardTitle>Noch kein Objekt</CardTitle>
            <CardDescription>
              Kosten hängen an einem Objekt. Legen Sie zuerst unter{' '}
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
      ) : buildingId ? (
        <CostsForBuilding
          key={buildingId}
          accountId={accountId}
          buildingId={buildingId}
          buildings={buildings.data.buildings}
          onBuildingChange={setSelectedId}
        />
      ) : null}
    </main>
  );
}

function CostsForBuilding({
  accountId,
  buildingId,
  buildings,
  onBuildingChange,
}: {
  accountId: string;
  buildingId: string;
  buildings: { id: string; name: string }[];
  onBuildingChange: (buildingId: string) => void;
}) {
  const costs = useCosts(accountId, buildingId);
  const detail = useBuildingDetail(accountId, buildingId);
  const units = detail.data?.units ?? [];
  const [requestedYear, setRequestedYear] = useState<number | null>(null);

  const yearsWithCosts = useMemo(() => {
    const years = new Set<number>();
    for (const cost of costs.data?.costs ?? []) {
      const start = Number(cost.periodFrom.slice(0, 4));
      const endExclusive = new Date(`${cost.periodTo}T00:00:00Z`);
      endExclusive.setUTCDate(endExclusive.getUTCDate() - 1);
      const end = endExclusive.getUTCFullYear();
      for (let year = start; year <= end; year += 1) years.add(year);
    }
    return [...years].sort((a, b) => b - a);
  }, [costs.data?.costs]);

  const yearOptions = useMemo(() => {
    const years = new Set(yearsWithCosts);
    years.add(new Date().getFullYear());
    return [...years].sort((a, b) => b - a);
  }, [yearsWithCosts]);
  const selectedYear =
    requestedYear !== null && yearOptions.includes(requestedYear)
      ? requestedYear
      : (yearsWithCosts[0] ?? yearOptions[0] ?? new Date().getFullYear());
  const visibleCosts = (costs.data?.costs ?? []).filter(
    (cost) =>
      cost.periodFrom < `${selectedYear + 1}-01-01` && cost.periodTo > `${selectedYear}-01-01`,
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-mint bg-card p-4">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {buildings.length > 1 ? (
            <div className="flex flex-wrap gap-2" role="group" aria-label="Objekt wählen">
              {buildings.map((building) => {
                const active = building.id === buildingId;
                return (
                  <Button
                    key={building.id}
                    variant={active ? 'secondary' : 'ghost'}
                    size="sm"
                    aria-pressed={active}
                    onClick={() => onBuildingChange(building.id)}
                  >
                    {building.name}
                  </Button>
                );
              })}
            </div>
          ) : (
            <p className="font-display font-semibold text-forest">{buildings[0]?.name}</p>
          )}
        </div>
        <Button asChild>
          <Link href={`/a/${accountId}/kosten/neu?objektId=${buildingId}`}>Kosten erfassen</Link>
        </Button>
      </div>

      {costs.isPending ? (
        <div
          aria-hidden="true"
          className="h-48 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      ) : costs.isError ? (
        <StatusNote kind="danger" label="Kosten konnten nicht geladen werden.">
          Bitte erneut versuchen.
        </StatusNote>
      ) : costs.data.costs.length === 0 ? (
        <Card className="border-l-4 border-l-green">
          <CardHeader>
            <CardTitle>Noch keine Kosten erfasst</CardTitle>
            <CardDescription>
              Erfassen Sie über „Kosten erfassen“ die erste Kostenart — z. B. Müllabfuhr 1.200,00 €
              nach Wohnfläche.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <Card className="border-l-4 border-l-green">
          <CardHeader className="flex-row flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle>Erfasste Kosten</CardTitle>
              <CardDescription>Aktive Kostenarten des gewählten Objekts.</CardDescription>
            </div>
            <div className="flex min-w-40 flex-col gap-1.5">
              <Label htmlFor="cost-year">Abrechnungsjahr</Label>
              <Select
                id="cost-year"
                value={selectedYear}
                onChange={(event) => setRequestedYear(Number(event.target.value))}
              >
                {yearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {visibleCosts.length === 0 ? (
              <p className="rounded-lg bg-paper p-4 text-sm text-slate">
                Für {selectedYear} sind keine Kosten erfasst.
              </p>
            ) : (
              <Table>
                <TableCaption>
                  Erfasste Kostenarten mit Umlageschlüssel, Status und Stornierungsaktion.
                </TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kostenart</TableHead>
                    <TableHead className="text-right">Betrag</TableHead>
                    <TableHead>Zeitraum</TableHead>
                    <TableHead>Umlageschlüssel</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>
                      <span className="sr-only">Aktion</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleCosts.map((cost) => (
                    <CostRow
                      key={cost.id}
                      cost={cost}
                      accountId={accountId}
                      buildingId={buildingId}
                      units={units.map((unit) => ({ id: unit.id, label: unit.label }))}
                    />
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CostRow({
  cost,
  accountId,
  buildingId,
  units,
}: {
  cost: CostEntryOut;
  accountId: string;
  buildingId: string;
  units: { id: string; label: string }[];
}) {
  const reassign = useReassignKey(accountId, buildingId);
  const voidCost = useVoidCost(accountId, buildingId);
  const [confirmingVoid, setConfirmingVoid] = useState(false);
  const [voidReason, setVoidReason] = useState('');
  const selectId = `key-${cost.id}`;

  function onKeyChange(next: AllocationKey) {
    if (next === cost.key) return;
    const directUnitId = next === 'DIRECT' ? units[0]?.id : undefined;
    if (next === 'DIRECT' && !directUnitId) return;
    reassign.mutate({ costId: cost.id, key: next, directUnitId });
  }

  const directLabel =
    cost.key === 'DIRECT'
      ? (units.find((unit) => unit.id === cost.directUnitId)?.label ?? 'unbekannte Einheit')
      : null;
  const findings = cost.classificationFindings;
  const hasStatus = cost.productionBlocked !== undefined && findings !== undefined;

  return (
    <TableRow>
      <TableCell className="align-top font-semibold">{cost.label}</TableCell>
      <TableCell className="align-top text-right tabular-nums">{cost.amountEur}</TableCell>
      <TableCell className="align-top text-sm text-slate">
        {isoToGermanDate(cost.periodFrom)} – {isoToGermanDate(cost.periodTo)}
      </TableCell>
      <TableCell className="align-top">
        {cost.key === null ? (
          <span className="text-sm text-slate">—</span>
        ) : (
          <>
            <Label htmlFor={selectId} className="sr-only">
              Umlageschlüssel für {cost.label}
            </Label>
            <Select
              id={selectId}
              value={cost.key}
              disabled={reassign.isPending}
              onChange={(event) => onKeyChange(event.target.value as AllocationKey)}
              className="min-w-64"
            >
              {ALLOCATION_KEYS.map((key) => (
                <option key={key} value={key} disabled={key === 'DIRECT' && units.length === 0}>
                  {ALLOCATION_KEY_LABELS[key]}
                </option>
              ))}
            </Select>
            {directLabel ? <p className="mt-1 text-xs text-slate">→ {directLabel}</p> : null}
            {reassign.isSuccess ? (
              <p role="status" className="mt-1 text-xs font-medium text-success">
                Gespeichert · {cost.assignmentCount}{' '}
                {cost.assignmentCount === 1 ? 'Schlüssel-Version' : 'Schlüssel-Versionen'}
              </p>
            ) : null}
            {reassign.isError ? (
              <p role="alert" className="mt-1 text-xs font-medium text-danger">
                Wechsel fehlgeschlagen.
              </p>
            ) : null}
          </>
        )}
      </TableCell>
      <TableCell className="min-w-48 align-top">
        {hasStatus ? (
          <div>
            <span
              className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                cost.productionBlocked
                  ? 'bg-warning-tint text-warning'
                  : 'bg-success-tint text-forest'
              }`}
            >
              {cost.productionBlocked ? 'Prüfen' : 'Abrechnungsreif'}
            </span>
            {findings.length > 0 ? (
              <ul className="mt-2 space-y-1 text-xs text-slate">
                {findings.map((finding) => (
                  <li key={finding}>{FINDING_LABELS[finding] ?? finding}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : (
          <span className="text-sm text-slate">—</span>
        )}
      </TableCell>
      <TableCell className="align-top">
        {confirmingVoid ? (
          <div className="flex min-w-64 flex-col items-start gap-2">
            <Label htmlFor={`void-reason-${cost.id}`}>Grund der Stornierung</Label>
            <Input
              id={`void-reason-${cost.id}`}
              value={voidReason}
              maxLength={500}
              placeholder="z. B. doppelt erfasst"
              onChange={(event) => setVoidReason(event.target.value)}
            />
            <div className="flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                disabled={voidCost.isPending || voidReason.trim() === ''}
                onClick={() =>
                  voidCost.mutate(
                    { costId: cost.id, reason: voidReason.trim() },
                    { onSuccess: () => setConfirmingVoid(false) },
                  )
                }
              >
                {voidCost.isPending ? 'Wird storniert…' : 'Stornieren'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirmingVoid(false)}>
                Abbrechen
              </Button>
            </div>
            {voidCost.isError ? (
              <p role="alert" className="text-xs font-medium text-danger">
                Stornierung fehlgeschlagen.
              </p>
            ) : null}
          </div>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="text-danger hover:bg-danger-tint"
            onClick={() => setConfirmingVoid(true)}
          >
            Stornieren
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
