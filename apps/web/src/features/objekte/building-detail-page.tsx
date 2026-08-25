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
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageHeader } from '@/features/portal/page-header';
import { ApiError } from '@/lib/api';
import { parseSqmToX100 } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
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

/** Objekt-Detail (docs/04): units of one building; create Unit. */
export function BuildingDetailPage({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const detail = useBuildingDetail(accountId, buildingId);

  if (detail.isPending) {
    return (
      <main className="py-10">
        <div
          aria-hidden="true"
          className="h-64 max-w-5xl animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      </main>
    );
  }
  if (detail.isError) {
    const missing = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <main className="py-10">
        <StatusNote kind="danger" label={missing ? 'Objekt nicht gefunden.' : 'Fehler beim Laden.'}>
          {missing ? (
            <Link className="underline underline-offset-4" href={`/a/${accountId}/objekte`}>
              Zurück zur Objektliste
            </Link>
          ) : (
            'Laden Sie die Seite neu oder versuchen Sie es später erneut.'
          )}
        </StatusNote>
      </main>
    );
  }

  const building = detail.data;
  return (
    <main className="py-10">
      <PageHeader
        title={building.name}
        description={`${building.street}, ${building.postalCode} ${building.city}`}
        breadcrumb={
          <Link
            href={`/a/${accountId}/objekte`}
            className="text-green underline-offset-4 hover:underline"
          >
            Objekte
          </Link>
        }
      />

      <div className="grid max-w-5xl gap-8 lg:grid-cols-[2fr_1fr]">
        <section aria-label="Einheiten">
          {building.units.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Einheiten</CardTitle>
                <CardDescription>
                  Legen Sie rechts die erste Wohneinheit an — Mietverhältnisse folgen auf der
                  Einheitenseite.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <Table>
                  <TableCaption>Einheiten in {building.name}</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Einheit</TableHead>
                      <TableHead className="text-right">Wohnfläche</TableHead>
                      <TableHead>Status heute</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {building.units.map((unit) => (
                      <TableRow key={unit.id}>
                        <TableCell>
                          <Link
                            href={`/a/${accountId}/einheiten/${unit.id}`}
                            className="font-semibold text-green underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                          >
                            {unit.label}
                          </Link>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {unit.areaSqm.toLocaleString('de-DE')} m²
                        </TableCell>
                        <TableCell className={unit.occupiedToday ? 'text-success' : 'text-slate'}>
                          {unit.occupiedToday ? 'Vermietet' : 'Leerstand'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </section>

        <CreateUnitForm accountId={accountId} buildingId={buildingId} />
      </div>
    </main>
  );
}

function CreateUnitForm({ accountId, buildingId }: { accountId: string; buildingId: string }) {
  const create = useCreateUnit(accountId, buildingId);
  const form = useForm<UnitForm>({ resolver: zodResolver(UnitFormSchema), defaultValues: EMPTY });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${buildingId}.unit-create`,
    form,
  );

  const onSubmit = form.handleSubmit((values) => {
    const areaSqmX100 = parseSqmToX100(values.areaSqm);
    if (areaSqmX100 === null) return; // zod already guards this
    create.mutate(
      { label: values.label, areaSqmX100 },
      {
        onSuccess: () => {
          clearDraft();
          form.reset(EMPTY);
        },
      },
    );
  });

  return (
    <section aria-label="Einheit anlegen">
      <Card>
        <CardHeader>
          <CardTitle>Einheit anlegen</CardTitle>
          <CardDescription>
            Eingaben werden automatisch als Entwurf gespeichert — nichts geht beim Abbrechen
            verloren.
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
            {create.isSuccess ? (
              <StatusNote kind="success" label="Gespeichert.">
                Die Einheit wurde angelegt.
              </StatusNote>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
