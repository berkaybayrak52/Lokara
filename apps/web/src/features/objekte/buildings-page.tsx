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

import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { useBuildings, useCreateBuilding } from './queries';

const BuildingFormSchema = z.object({
  name: z.string().min(1, 'Pflichtfeld'),
  street: z.string().min(1, 'Pflichtfeld'),
  postalCode: z.string().regex(/^\d{5}$/, 'PLZ: genau 5 Ziffern'),
  city: z.string().min(1, 'Pflichtfeld'),
});
type BuildingForm = z.infer<typeof BuildingFormSchema>;

const EMPTY: BuildingForm = { name: '', street: '', postalCode: '', city: '' };

/** Objekte (docs/04 M3 page 2): list → detail; create Building. */
export function BuildingsPage({ accountId }: { accountId: string }) {
  const buildings = useBuildings(accountId);

  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Objekte</h1>
        <p className="mt-2 max-w-prose text-slate">
          Gebäude mit ihren Einheiten und Mietverhältnissen. Ein Klick auf ein Objekt öffnet die
          Einheiten.
        </p>
      </header>

      <div className="grid max-w-5xl gap-8 lg:grid-cols-[2fr_1fr]">
        <section aria-label="Objektliste">
          {buildings.isPending ? (
            <div aria-hidden="true" className="h-48 animate-pulse rounded-xl bg-mint/60" />
          ) : buildings.isError ? (
            <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
              Bitte API und Datenbank prüfen, dann neu laden.
            </StatusNote>
          ) : buildings.data.buildings.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Objekte</CardTitle>
                <CardDescription>
                  Legen Sie rechts Ihr erstes Gebäude an — Einheiten und Mietverhältnisse folgen
                  auf der Detailseite.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <Table>
                  <TableCaption>Alle Objekte dieses Kontos</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Objekt</TableHead>
                      <TableHead>Adresse</TableHead>
                      <TableHead className="text-right">Einheiten</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {buildings.data.buildings.map((b) => (
                      <TableRow key={b.id}>
                        <TableCell>
                          <Link
                            href={`/a/${accountId}/objekte/${b.id}`}
                            className="font-semibold text-green underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                          >
                            {b.name}
                          </Link>
                        </TableCell>
                        <TableCell className="text-slate">
                          {b.street}, {b.postalCode} {b.city}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{b.unitCount}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </section>

        <CreateBuildingForm accountId={accountId} />
      </div>
    </main>
  );
}

function CreateBuildingForm({ accountId }: { accountId: string }) {
  const create = useCreateBuilding(accountId);
  const form = useForm<BuildingForm>({
    resolver: zodResolver(BuildingFormSchema),
    defaultValues: EMPTY,
  });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.building-create`, form);

  const onSubmit = form.handleSubmit((values) => {
    create.mutate(values, {
      onSuccess: () => {
        clearDraft();
        form.reset(EMPTY);
      },
    });
  });

  return (
    <section aria-label="Objekt anlegen">
      <Card>
        <CardHeader>
          <CardTitle>Objekt anlegen</CardTitle>
          <CardDescription>
            Eingaben werden automatisch als Entwurf gespeichert — nichts geht beim Abbrechen
            verloren.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
            <FormField
              id="building-name"
              label="Bezeichnung"
              hint="z. B. Musterstraße 12"
              error={form.formState.errors.name}
              registration={form.register('name')}
            />
            <FormField
              id="building-street"
              label="Straße und Hausnummer"
              error={form.formState.errors.street}
              registration={form.register('street')}
            />
            <div className="grid grid-cols-[120px_1fr] gap-4">
              <FormField
                id="building-plz"
                label="PLZ"
                inputMode="numeric"
                error={form.formState.errors.postalCode}
                registration={form.register('postalCode')}
              />
              <FormField
                id="building-city"
                label="Ort"
                error={form.formState.errors.city}
                registration={form.register('city')}
              />
            </div>
            <div>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Wird angelegt…' : 'Objekt anlegen'}
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
                Das Objekt wurde angelegt.
              </StatusNote>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
