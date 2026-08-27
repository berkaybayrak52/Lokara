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
} from '@lokara/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { useBuildings } from '@/features/objekte/queries';
import { PageHeader } from '@/features/portal/page-header';
import { ApiError } from '@/lib/api';

import { useCreateStatementDraft, useStatementPeriodSuggestions } from './queries';

export function StatementStartPage({
  accountId,
  initialBuildingId,
}: {
  accountId: string;
  initialBuildingId?: string;
}) {
  const router = useRouter();
  const buildings = useBuildings(accountId);
  const options = buildings.data?.buildings ?? [];
  const initialSelection = useMemo(() => {
    if (initialBuildingId && options.some((building) => building.id === initialBuildingId)) {
      return initialBuildingId;
    }
    return options.length === 1 ? (options[0]?.id ?? '') : '';
  }, [initialBuildingId, options]);
  const [selectedBuildingId, setSelectedBuildingId] = useState('');
  const buildingId = selectedBuildingId || initialSelection;
  const suggestions = useStatementPeriodSuggestions(accountId, buildingId);
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const create = useCreateStatementDraft(accountId);

  useEffect(() => {
    const suggestion = suggestions.data?.[0];
    if (suggestion && periodStart === '' && periodEnd === '') {
      setPeriodStart(suggestion.periodStart);
      setPeriodEnd(suggestion.periodEnd);
    }
  }, [periodEnd, periodStart, suggestions.data]);

  return (
    <main className="py-10">
      <PageHeader
        title="Neue Abrechnung"
        description="Wählen Sie ein Objekt und den Abrechnungszeitraum. Danach wird ein wiederaufnehmbarer Entwurf angelegt."
      />
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Objekt und Zeitraum</CardTitle>
          <CardDescription>
            Anfang und Ende zählen mit. Zeitraumregeln und Datenlage prüft der Server.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="draft-building">Objekt</Label>
            <Select
              id="draft-building"
              value={buildingId}
              disabled={options.length === 0}
              onChange={(event) => {
                setSelectedBuildingId(event.target.value);
                setPeriodStart('');
                setPeriodEnd('');
              }}
            >
              <option value="">Objekt wählen</option>
              {options.map((building) => (
                <option key={building.id} value={building.id}>
                  {building.name} - {building.street}, {building.postalCode} {building.city}
                </option>
              ))}
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="draft-period-start">Zeitraum von</Label>
              <Input
                id="draft-period-start"
                type="date"
                value={periodStart}
                onChange={(event) => setPeriodStart(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="draft-period-end">Zeitraum bis</Label>
              <Input
                id="draft-period-end"
                type="date"
                value={periodEnd}
                onChange={(event) => setPeriodEnd(event.target.value)}
              />
            </div>
          </div>
          {suggestions.data?.[0] ? (
            <p className="text-sm text-slate">{suggestions.data[0].reason}</p>
          ) : null}
          {options.length === 0 ? (
            <StatusNote kind="warning" label="Noch kein Objekt vorhanden.">
              Legen Sie zuerst ein Objekt an oder laden Sie das Demo-Szenario.
            </StatusNote>
          ) : null}
          {create.isError ? (
            <StatusNote kind="danger" label="Entwurf konnte nicht angelegt werden.">
              {create.error instanceof ApiError && create.error.detail
                ? create.error.detail
                : 'Bitte prüfen Sie Objekt und Zeitraum.'}
            </StatusNote>
          ) : null}
          <div className="flex flex-wrap gap-3">
            <Button
              disabled={!buildingId || !periodStart || !periodEnd || create.isPending}
              onClick={() =>
                create.mutate(
                  { buildingId, periodStart, periodEnd },
                  {
                    onSuccess: (draft) => router.push(`/a/${accountId}/abrechnung/${draft.id}`),
                  },
                )
              }
            >
              Weiter
            </Button>
            <Button asChild variant="outline">
              <Link href={`/a/${accountId}/abrechnung`}>Abbrechen</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
