'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  StatusNote,
} from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageHeader } from '@/features/portal/page-header';
import { ApiError } from '@/lib/api';
import { parseSqmToX100 } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { InactivePhotoSlot } from './inactive-photo-slot';
import { useBuildingDetail, useCreateUnit } from './queries';

const UnitFormSchema = z.object({
  label: z.string().trim().min(1, 'Pflichtfeld').max(200, 'Maximal 200 Zeichen'),
  areaSqm: z
    .string()
    .min(1, 'Pflichtfeld')
    .refine((value) => parseSqmToX100(value) !== null, 'Fläche wie 64,50 angeben')
    .refine((value) => (parseSqmToX100(value) ?? 0) > 0, 'Fläche muss größer als 0 sein'),
});
type UnitForm = z.infer<typeof UnitFormSchema>;

const EMPTY: UnitForm = { label: '', areaSqm: '' };

interface CreatedUnit {
  id: string;
  label: string;
}

export function UnitWizard({
  accountId,
  buildingId,
  buildingName,
}: {
  accountId: string;
  buildingId: string;
  buildingName: string;
}) {
  const create = useCreateUnit(accountId, buildingId);
  const [createdUnit, setCreatedUnit] = useState<CreatedUnit | null>(null);
  const form = useForm<UnitForm>({ resolver: zodResolver(UnitFormSchema), defaultValues: EMPTY });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${buildingId}.unit-create`,
    form,
  );

  const onSubmit = form.handleSubmit((values) => {
    const areaSqmX100 = parseSqmToX100(values.areaSqm);
    if (areaSqmX100 === null) return;
    create.mutate(
      { label: values.label, areaSqmX100 },
      {
        onSuccess: (created) => {
          clearDraft();
          setCreatedUnit({ id: created.id, label: created.label });
        },
      },
    );
  });

  const startAnother = () => {
    clearDraft();
    form.reset(EMPTY);
    setCreatedUnit(null);
  };

  return (
    <main className="py-10">
      <PageHeader
        title={`Einheit anlegen — ${buildingName}`}
        breadcrumb={
          <Link
            className="text-green underline-offset-4 hover:underline"
            href={`/a/${accountId}/objekte/${buildingId}`}
          >
            {buildingName}
          </Link>
        }
      />

      {createdUnit ? (
        <Card role="status" aria-label="Einheit angelegt" className="max-w-3xl">
          <CardHeader>
            <CardTitle>Einheit angelegt</CardTitle>
            <CardDescription>{createdUnit.label} wurde gespeichert.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button type="button" variant="secondary" onClick={startAnother}>
              Noch eine Einheit anlegen
            </Button>
            <Button asChild variant="outline">
              <Link href={`/a/${accountId}/einheiten/${createdUnit.id}`}>Zur Einheit</Link>
            </Button>
            <Button asChild>
              <Link href={`/a/${accountId}/objekte/${buildingId}`}>Fertig — zum Objekt</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="max-w-3xl">
          <CardHeader>
            <CardTitle>Neue Einheit</CardTitle>
            <CardDescription>
              Eingaben werden automatisch als Entwurf gespeichert — nichts geht verloren.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
              <FormField
                id="unit-label"
                label="Bezeichnung"
                hint="z. B. Wohnung 1 (EG links)"
                error={form.formState.errors.label}
                registration={form.register('label')}
              />
              <FormField
                id="unit-area"
                label="Wohnfläche in m²"
                hint="z. B. 64,50"
                inputMode="decimal"
                error={form.formState.errors.areaSqm}
                registration={form.register('areaSqm')}
              />
              <InactivePhotoSlot />
              <div>
                <Button type="submit" disabled={create.isPending}>
                  {create.isPending ? 'Wird angelegt…' : 'Einheit anlegen'}
                </Button>
              </div>
              {draftRestored ? (
                <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
                  Ihre letzten Eingaben wurden automatisch gesichert.
                </StatusNote>
              ) : null}
              {create.isError ? (
                <StatusNote kind="danger" label="Anlegen fehlgeschlagen.">
                  Bitte Eingaben prüfen und erneut versuchen.
                </StatusNote>
              ) : null}
            </form>
          </CardContent>
        </Card>
      )}
    </main>
  );
}

export function UnitWizardPage({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const detail = useBuildingDetail(accountId, buildingId);
  if (detail.isPending) {
    return (
      <div
        aria-hidden="true"
        className="h-64 max-w-3xl animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
      />
    );
  }
  if (detail.isError) {
    const missing = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <StatusNote kind="danger" label={missing ? 'Objekt nicht gefunden.' : 'Fehler beim Laden.'}>
        <Link className="underline underline-offset-4" href={`/a/${accountId}/objekte`}>
          Zurück zur Objektliste
        </Link>
      </StatusNote>
    );
  }
  return (
    <UnitWizard accountId={accountId} buildingId={buildingId} buildingName={detail.data.name} />
  );
}
