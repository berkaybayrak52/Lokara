'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, StatusNote } from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageHeader } from '@/features/portal/page-header';
import { parseSqmToX100 } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { PhotoSlot } from './photo-slot';
import { useBuildingDetail, useCreateUnit } from './queries';

const UnitFormSchema = z.object({
  label: z.string().min(1, 'Pflichtfeld'),
  areaSqm: z
    .string()
    .min(1, 'Pflichtfeld')
    .refine((value) => parseSqmToX100(value) !== null, 'Fläche wie 64,50 angeben')
    .refine((value) => (parseSqmToX100(value) ?? 0) > 0, 'Fläche muss größer als 0 sein'),
});
type UnitForm = z.infer<typeof UnitFormSchema>;

const EMPTY: UnitForm = { label: '', areaSqm: '' };

interface Created {
  id: string;
  label: string;
}

/** Wizard-B (O10): einstufig, mit Bestätigung und „noch eine Einheit anlegen". */
export function UnitWizard({ accountId, buildingId }: { accountId: string; buildingId: string }) {
  const detail = useBuildingDetail(accountId, buildingId);
  const buildingName = detail.data?.name ?? 'Objekt';
  const create = useCreateUnit(accountId, buildingId);
  const [created, setCreated] = useState<Created | null>(null);

  const form = useForm<UnitForm>({ resolver: zodResolver(UnitFormSchema), defaultValues: EMPTY });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.${buildingId}.unit-create`, form);

  const onSubmit = form.handleSubmit((values) => {
    const areaSqmX100 = parseSqmToX100(values.areaSqm);
    if (areaSqmX100 === null) return;
    create.mutate(
      { label: values.label, areaSqmX100 },
      {
        onSuccess: (unit) => {
          clearDraft();
          form.reset(EMPTY);
          setCreated({ id: unit.id, label: unit.label });
        },
      },
    );
  });

  if (created) {
    return (
      <main className="py-10">
        <PageHeader title={`Einheit anlegen — ${buildingName}`} />
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle>Einheit angelegt</CardTitle>
            <CardDescription>„{created.label}" wurde angelegt.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button onClick={() => setCreated(null)}>Noch eine Einheit anlegen</Button>
            <Button asChild variant="outline">
              <Link href={`/a/${accountId}/einheiten/${created.id}`}>Zur Einheit</Link>
            </Button>
            <Button asChild variant="ghost">
              <Link href={`/a/${accountId}/objekte/${buildingId}`}>Fertig — zum Objekt</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="py-10">
      <PageHeader title={`Einheit anlegen — ${buildingName}`} />
      <Card className="max-w-2xl">
        <CardContent className="pt-6">
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
            <PhotoSlot />
            <div className="flex gap-2">
              <Button asChild variant="outline">
                <Link href={`/a/${accountId}/objekte/${buildingId}`}>Zurück</Link>
              </Button>
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
    </main>
  );
}
