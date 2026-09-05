'use client';

import { zodResolver } from '@hookform/resolvers/zod';
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
} from '@lokara/ui';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';

import { FormField } from '@/features/objekte/form-field';
import { useBuildingDetail, useBuildings } from '@/features/objekte/queries';
import { PageHeader } from '@/features/portal/page-header';
import { ApiError } from '@/lib/api';
import type { CostCataloguePosition } from '@/lib/contracts';
import { ALLOCATION_KEYS, ALLOCATION_KEY_LABELS } from '@/lib/contracts';
import { useFormDraft } from '@/lib/form-draft';

import { CostFormSchema, EMPTY_COST_FORM, toCostCreateInput, type CostForm } from './cost-form';
import { useCostCatalogue, useCreateCost } from './queries';

export function CostWizard({
  accountId,
  initialBuildingId,
}: {
  accountId: string;
  initialBuildingId: string | null;
}) {
  const buildings = useBuildings(accountId);
  const [requestedBuildingId, setRequestedBuildingId] = useState(initialBuildingId ?? '');
  const requestedExists = buildings.data?.buildings.some(
    (building) => building.id === requestedBuildingId,
  );
  const buildingId =
    requestedExists === true
      ? requestedBuildingId
      : buildings.data?.buildings.length === 1
        ? (buildings.data.buildings[0]?.id ?? '')
        : '';

  return (
    <main className="py-10">
      <PageHeader
        title="Kosten erfassen"
        description="Neue Kostenart für ein Objekt anlegen. Eingaben werden automatisch als Entwurf gespeichert."
        breadcrumb={
          <Link
            className="text-green underline-offset-4 hover:underline"
            href={`/a/${accountId}/kosten${buildingId ? `?objektId=${buildingId}` : ''}`}
          >
            Zur Kostenliste
          </Link>
        }
      />

      {buildings.isPending ? (
        <div
          aria-hidden="true"
          className="h-80 max-w-3xl animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      ) : buildings.isError ? (
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          Bitte erneut versuchen.
        </StatusNote>
      ) : buildings.data.buildings.length === 0 ? (
        <Card className="max-w-xl border-l-4 border-l-green">
          <CardHeader>
            <CardTitle>Noch kein Objekt</CardTitle>
            <CardDescription>
              Legen Sie zuerst ein Objekt an, bevor Sie Kosten erfassen.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href={`/a/${accountId}/objekte/neu`}>Objekt anlegen</Link>
            </Button>
          </CardContent>
        </Card>
      ) : buildingId === '' ? (
        <Card className="max-w-3xl border-l-4 border-l-green">
          <CardHeader>
            <CardTitle>Objekt wählen</CardTitle>
            <CardDescription>Für welches Objekt möchten Sie Kosten erfassen?</CardDescription>
          </CardHeader>
          <CardContent>
            <Label htmlFor="wizard-building">Objekt</Label>
            <Select
              id="wizard-building"
              className="mt-2 max-w-md"
              value={requestedBuildingId}
              onChange={(event) => setRequestedBuildingId(event.target.value)}
            >
              <option value="">Objekt wählen …</option>
              {buildings.data.buildings.map((building) => (
                <option key={building.id} value={building.id}>
                  {building.name}
                </option>
              ))}
            </Select>
          </CardContent>
        </Card>
      ) : (
        <CostFormCard
          key={buildingId}
          accountId={accountId}
          buildingId={buildingId}
          buildingName={
            buildings.data.buildings.find((building) => building.id === buildingId)?.name ??
            'Objekt'
          }
        />
      )}
    </main>
  );
}

function CostFormCard({
  accountId,
  buildingId,
  buildingName,
}: {
  accountId: string;
  buildingId: string;
  buildingName: string;
}) {
  const catalogue = useCostCatalogue(accountId);
  const detail = useBuildingDetail(accountId, buildingId);
  const create = useCreateCost(accountId, buildingId);
  const [search, setSearch] = useState('');
  const [completed, setCompleted] = useState(false);
  const form = useForm<CostForm>({
    resolver: zodResolver(CostFormSchema),
    defaultValues: EMPTY_COST_FORM,
  });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${buildingId}.cost-create`,
    form,
  );
  const catalogueId = form.watch('catalogueId');
  const selectedKey = form.watch('key');
  const selectedPosition = catalogue.data?.positions.find(
    (position) => position.catalogueId === catalogueId,
  );
  const units = detail.data?.units ?? [];

  const filteredPositions = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase('de');
    const positions = catalogue.data?.positions ?? [];
    if (needle === '') return positions;
    return positions.filter((position) =>
      [position.label, position.betrkvNumber ?? '', position.catalogueId].some((value) =>
        value.toLocaleLowerCase('de').includes(needle),
      ),
    );
  }, [catalogue.data?.positions, search]);
  const allocablePositions = filteredPositions
    .filter((position) => position.allocable)
    .sort(compareCataloguePositions);
  const nonAllocablePositions = filteredPositions
    .filter((position) => !position.allocable)
    .sort(compareCataloguePositions);

  function choosePosition(catalogueIdValue: string) {
    const position = catalogue.data?.positions.find(
      (candidate) => candidate.catalogueId === catalogueIdValue,
    );
    form.setValue('catalogueId', catalogueIdValue, { shouldDirty: true, shouldValidate: true });
    form.setValue('key', position?.defaultKey ?? '', { shouldDirty: true, shouldValidate: true });
    form.setValue('directUnitId', '', { shouldDirty: true });
  }

  const onSubmit = form.handleSubmit((values) => {
    if (!selectedPosition) {
      form.setError('catalogueId', { message: 'Bitte eine Kostenart wählen' });
      return;
    }
    if (selectedPosition.allocable && values.key === '') {
      form.setError('key', { message: 'Bitte einen Umlageschlüssel wählen' });
      return;
    }
    const input = toCostCreateInput(values, selectedPosition.label, selectedPosition.defaultKey);
    if (input === null) return;
    create.mutate(input, {
      onSuccess: () => {
        clearDraft();
        setCompleted(true);
      },
    });
  });

  function startAnother() {
    create.reset();
    form.reset(EMPTY_COST_FORM);
    setSearch('');
    setCompleted(false);
  }

  if (completed) {
    return (
      <Card className="max-w-3xl border-l-4 border-l-green">
        <CardHeader>
          <CardTitle>Kostenart erfasst.</CardTitle>
          <CardDescription>Die Kostenart wurde für {buildingName} gespeichert.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button type="button" onClick={startAnother}>
            Noch eine Kostenart erfassen
          </Button>
          <Button asChild variant="outline">
            <Link href={`/a/${accountId}/kosten?objektId=${buildingId}`}>Fertig</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="max-w-3xl border-l-4 border-l-green">
      <CardHeader>
        <CardTitle>Manuell erfassen</CardTitle>
        <CardDescription>{buildingName}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <div>
          <div className="inline-flex rounded-lg bg-mint p-1" aria-label="Erfassungsart">
            <span className="rounded-md bg-card px-4 py-2 text-sm font-semibold text-forest shadow-sm">
              Manuell erfassen
            </span>
            <button
              type="button"
              disabled
              tabIndex={-1}
              className="cursor-not-allowed rounded-md px-4 py-2 text-sm font-semibold text-slate opacity-60"
            >
              Aus Beleg <span className="text-xs">(Beta)</span>
            </button>
          </div>
          <p className="mt-2 text-sm text-slate">Automatische Belegerkennung kommt bald.</p>
        </div>

        {catalogue.isPending ? (
          <div
            aria-hidden="true"
            className="h-24 animate-pulse rounded-lg bg-mint/60 motion-reduce:animate-none"
          />
        ) : catalogue.isError ? (
          <StatusNote kind="danger" label="BetrKV-Katalog konnte nicht geladen werden.">
            Kostenarten stehen momentan nicht zur Auswahl. Bitte versuchen Sie es erneut.
          </StatusNote>
        ) : (
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cost-catalogue-search">Kostenart (BetrKV)</Label>
              <Input
                id="cost-catalogue-search"
                type="search"
                value={search}
                placeholder="Kostenart suchen …"
                onChange={(event) => setSearch(event.target.value)}
              />
              <Select
                id="cost-catalogue"
                aria-label="Kostenart aus dem BetrKV-Katalog wählen"
                aria-invalid={form.formState.errors.catalogueId ? true : undefined}
                value={catalogueId}
                onChange={(event) => choosePosition(event.target.value)}
              >
                <option value="">Kostenart wählen …</option>
                {allocablePositions.length > 0 ? (
                  <optgroup label="Umlagefähig">
                    {allocablePositions.map((position) => (
                      <CatalogueOption key={position.catalogueId} position={position} />
                    ))}
                  </optgroup>
                ) : null}
                {nonAllocablePositions.length > 0 ? (
                  <optgroup label="Nicht umlagefähig">
                    {nonAllocablePositions.map((position) => (
                      <CatalogueOption key={position.catalogueId} position={position} />
                    ))}
                  </optgroup>
                ) : null}
              </Select>
              {form.formState.errors.catalogueId ? (
                <p className="text-sm font-medium text-danger">
                  {form.formState.errors.catalogueId.message}
                </p>
              ) : (
                <p className="text-sm text-slate">
                  Die Auswahl bestimmt die rechtliche Kostenart und den vorgeschlagenen Schlüssel.
                </p>
              )}
              {filteredPositions.length === 0 ? (
                <p className="text-sm text-slate">Keine passende Kostenart gefunden.</p>
              ) : null}
            </div>

            <FormField
              id="cost-label"
              label="Bezeichnung (optional)"
              hint="Eigene Benennung, z. B. Rechnungsnummer oder ‚Müllabfuhr Q1‘"
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
            <div className="grid gap-4 sm:grid-cols-2">
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

            {selectedPosition && !selectedPosition.allocable ? (
              <StatusNote kind="warning" label="Nicht umlagefähig.">
                Diese Kostenart ist nach BetrKV nicht auf Mieter umlagefähig. Sie kann erfasst, aber
                nicht auf die Mieter umgelegt werden.
              </StatusNote>
            ) : selectedPosition ? (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cost-key">Umlageschlüssel</Label>
                <Select
                  id="cost-key"
                  aria-invalid={form.formState.errors.key ? true : undefined}
                  {...form.register('key')}
                >
                  {ALLOCATION_KEYS.map((key) => (
                    <option key={key} value={key} disabled={key === 'DIRECT' && units.length === 0}>
                      {ALLOCATION_KEY_LABELS[key]}
                    </option>
                  ))}
                </Select>
                {form.formState.errors.key ? (
                  <p className="text-sm font-medium text-danger">
                    {form.formState.errors.key.message}
                  </p>
                ) : (
                  <p className="text-sm text-slate">
                    Später jederzeit änderbar, ohne Datenverlust.
                  </p>
                )}
              </div>
            ) : null}

            {selectedPosition?.allocable && selectedKey === 'DIRECT' ? (
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

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={create.isPending || selectedPosition === undefined}>
                {create.isPending
                  ? 'Wird erfasst…'
                  : selectedPosition?.allocable === false
                    ? 'Nicht umlagefähig erfassen'
                    : 'Kostenart erfassen'}
              </Button>
              <Button asChild variant="ghost">
                <Link href={`/a/${accountId}/kosten?objektId=${buildingId}`}>Abbrechen</Link>
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
                  ? (create.error.detail ?? 'Bitte Eingaben und Zeitraum prüfen.')
                  : 'Bitte erneut versuchen.'}
              </StatusNote>
            ) : null}
          </form>
        )}
      </CardContent>
    </Card>
  );
}

function compareCataloguePositions(left: CostCataloguePosition, right: CostCataloguePosition) {
  return left.label.localeCompare(right.label, 'de');
}

function CatalogueOption({ position }: { position: CostCataloguePosition }) {
  return (
    <option value={position.catalogueId}>
      {position.label}
      {position.betrkvNumber ? ` · § ${position.betrkvNumber}` : ''}
    </option>
  );
}
