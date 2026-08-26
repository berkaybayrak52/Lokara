'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
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
import { PageHeader } from '@/features/portal/page-header';
import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { useBuildingDetail, useBuildings } from '@/features/objekte/queries';
import { FormField } from '@/features/objekte/form-field';
import { ApiError } from '@/lib/api';
import type { AllocationKey, CostEntryOut } from '@/lib/contracts';
import { ALLOCATION_KEYS, ALLOCATION_KEY_LABELS } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { CostFormSchema, EMPTY_COST_FORM, toCostCreateInput, type CostForm } from './cost-form';
import { useCosts, useCreateCost, useDeleteCost, useReassignKey } from './queries';

/** Kosten erfassen (docs/04 M3 page 4). */
export function CostsPage({ accountId }: { accountId: string }) {
  const buildings = useBuildings(accountId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const buildingId = selectedId ?? buildings.data?.buildings[0]?.id ?? null;

  return (
    <main className="py-10">
      <PageHeader
        title="Kosten erfassen"
        description="Betriebskosten je Objekt und Abrechnungszeitraum. Der Umlageschlüssel wird pro Kostenart gewählt und kann jederzeit geändert werden — die Abrechnung rechnet neu, erfasste Daten bleiben erhalten."
      />

      {buildings.isPending ? (
        <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-mint/60" />
      ) : buildings.isError ? (
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          Laden Sie die Seite neu oder versuchen Sie es später erneut.
        </StatusNote>
      ) : buildings.data.buildings.length === 0 ? (
        <Card className="max-w-xl">
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
          {buildingId ? <CostsForBuilding accountId={accountId} buildingId={buildingId} /> : null}
        </>
      )}
    </main>
  );
}

function CostsForBuilding({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const costs = useCosts(accountId, buildingId);
  const detail = useBuildingDetail(accountId, buildingId);
  const units = detail.data?.units ?? [];

  return (
    <div className="grid gap-8 lg:grid-cols-[3fr_2fr]">
      <section aria-label="Erfasste Kosten">
        {costs.isPending ? (
          <div aria-hidden="true" className="h-48 animate-pulse rounded-xl bg-mint/60" />
        ) : costs.isError ? (
          <StatusNote kind="danger" label="Kosten konnten nicht geladen werden.">
            Bitte erneut versuchen.
          </StatusNote>
        ) : costs.data.costs.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>Noch keine Kosten erfasst</CardTitle>
              <CardDescription>
                Erfassen Sie rechts die erste Kostenart — z. B. Müllabfuhr 1.200,00 € nach
                Wohnfläche.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableCaption>
                  Erfasste Kostenarten mit ihrem Umlageschlüssel. Ein Wechsel des Schlüssels
                  löscht keine Daten.
                </TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kostenart</TableHead>
                    <TableHead className="text-right">Betrag</TableHead>
                    <TableHead>Zeitraum</TableHead>
                    <TableHead>Umlageschlüssel</TableHead>
                    <TableHead>
                      <span className="sr-only">Aktion</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {costs.data.costs.map((cost) => (
                    <CostRow
                      key={cost.id}
                      cost={cost}
                      accountId={accountId}
                      buildingId={buildingId}
                      units={units.map((u) => ({ id: u.id, label: u.label }))}
                    />
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </section>

      <CreateCostForm
        accountId={accountId}
        buildingId={buildingId}
        units={units.map((u) => ({ id: u.id, label: u.label }))}
      />
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
  const remove = useDeleteCost(accountId, buildingId);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const selectId = `key-${cost.id}`;

  function onKeyChange(next: AllocationKey) {
    if (next === cost.key) return;
    // DIRECT needs a target; default to the first unit so the switch never
    // dead-ends, then the row shows which unit it went to.
    const directUnitId = next === 'DIRECT' ? units[0]?.id : undefined;
    if (next === 'DIRECT' && !directUnitId) return;
    reassign.mutate({ costId: cost.id, key: next, directUnitId });
  }

  const directLabel =
    cost.key === 'DIRECT'
      ? (units.find((u) => u.id === cost.directUnitId)?.label ?? 'unbekannte Einheit')
      : null;

  return (
    <TableRow>
      <TableCell className="font-semibold">{cost.label}</TableCell>
      <TableCell className="text-right tabular-nums">{cost.amountEur}</TableCell>
      <TableCell className="text-sm text-slate">
        {isoToGermanDate(cost.periodFrom)} – {isoToGermanDate(cost.periodTo)}
      </TableCell>
      <TableCell>
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
      </TableCell>
      <TableCell>
        {/* Two-step delete: entered data never disappears on a single misclick
            (docs/04 "no data loss"). The quiet trigger keeps one filled action
            per screen; the filled destructive is the confirmation itself. */}
        {confirmingDelete ? (
          <div className="flex flex-col items-start gap-1.5">
            <p className="text-xs font-medium text-danger">Wirklich löschen?</p>
            <div className="flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                disabled={remove.isPending}
                onClick={() => remove.mutate(cost.id)}
              >
                {remove.isPending ? 'Löscht…' : 'Löschen'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirmingDelete(false)}>
                Abbrechen
              </Button>
            </div>
          </div>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="text-danger hover:bg-danger-tint"
            onClick={() => setConfirmingDelete(true)}
          >
            Löschen
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}

function CreateCostForm({
  accountId,
  buildingId,
  units,
}: {
  accountId: string;
  buildingId: string;
  units: { id: string; label: string }[];
}) {
  const create = useCreateCost(accountId, buildingId);
  const form = useForm<CostForm>({
    resolver: zodResolver(CostFormSchema),
    defaultValues: EMPTY_COST_FORM,
  });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.${buildingId}.cost-create`, form);
  const selectedKey = form.watch('key');

  const onSubmit = form.handleSubmit((values) => {
    const input = toCostCreateInput(values);
    if (input === null) return; // zod already guards this
    create.mutate(input, {
      onSuccess: () => {
        clearDraft();
        form.reset(EMPTY_COST_FORM);
      },
    });
  });

  return (
    <section aria-label="Kostenart erfassen">
      <Card>
        <CardHeader>
          <CardTitle>Kostenart erfassen</CardTitle>
          <CardDescription>
            Eingaben werden automatisch als Entwurf gespeichert — nichts geht beim Abbrechen
            verloren.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
            <FormField
              id="cost-label"
              label="Kostenart"
              hint="z. B. Müllabfuhr"
              error={form.formState.errors.label}
              registration={form.register('label')}
            />
            <FormField
              id="cost-amount"
              label="Betrag in € (Gesamtkosten)"
              hint="z. B. 1.200,00"
              inputMode="decimal"
              error={form.formState.errors.amount}
              registration={form.register('amount')}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                id="cost-from"
                label="Zeitraum von"
                type="date"
                error={form.formState.errors.periodFrom}
                registration={form.register('periodFrom')}
              />
              <FormField
                id="cost-to"
                label="bis (exklusiv)"
                type="date"
                error={form.formState.errors.periodTo}
                registration={form.register('periodTo')}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cost-key">Umlageschlüssel</Label>
              <Select id="cost-key" {...form.register('key')}>
                {ALLOCATION_KEYS.map((key) => (
                  <option key={key} value={key} disabled={key === 'DIRECT' && units.length === 0}>
                    {ALLOCATION_KEY_LABELS[key]}
                  </option>
                ))}
              </Select>
              <p className="text-sm text-slate">Später jederzeit änderbar, ohne Datenverlust.</p>
            </div>
            {selectedKey === 'DIRECT' ? (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cost-direct-unit">Direkt zuordnen an</Label>
                <Select
                  id="cost-direct-unit"
                  aria-invalid={form.formState.errors.directUnitId ? true : undefined}
                  {...form.register('directUnitId')}
                >
                  <option value="">Einheit wählen …</option>
                  {units.map((unit) => (
                    <option key={unit.id} value={unit.id}>
                      {unit.label}
                    </option>
                  ))}
                </Select>
                {form.formState.errors.directUnitId ? (
                  <p className="text-sm font-medium text-danger">
                    {form.formState.errors.directUnitId.message}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Wird erfasst…' : 'Kostenart erfassen'}
              </Button>
            </div>
            {draftRestored ? (
              <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
                Ihre letzten Eingaben wurden automatisch gesichert.
              </StatusNote>
            ) : null}
            {create.isError ? (
              <StatusNote kind="danger" label="Erfassen fehlgeschlagen.">
                {create.error instanceof ApiError && create.error.status === 422
                  ? 'Bitte Zeitraum und Umlageschlüssel prüfen.'
                  : 'Bitte erneut versuchen.'}
              </StatusNote>
            ) : null}
            {create.isSuccess ? (
              <StatusNote kind="success" label="Gespeichert.">
                Die Kostenart wurde erfasst und fließt in die Abrechnung ein.
              </StatusNote>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
