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

import { ApiError } from '@/lib/api';
import { isoToGermanDate, parseEurToCents } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { TenancyTimeline } from './tenancy-timeline';
import { useCreateTenancy, useUnitDetail } from './queries';

const TenancyFormSchema = z
  .object({
    renterName: z.string().min(1, 'Pflichtfeld'),
    validFrom: z.string().min(1, 'Pflichtfeld'),
    validTo: z.string(), // optional: empty = unbefristet
    baseRent: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((v) => parseEurToCents(v) !== null, 'Betrag wie 950,00 angeben'),
    advance: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((v) => parseEurToCents(v) !== null, 'Betrag wie 220,00 angeben'),
  })
  .refine((values) => values.validTo === '' || values.validTo > values.validFrom, {
    path: ['validTo'],
    message: 'Ende muss nach dem Beginn liegen',
  });
type TenancyForm = z.infer<typeof TenancyFormSchema>;

const EMPTY: TenancyForm = { renterName: '', validFrom: '', validTo: '', baseRent: '', advance: '' };

/** Einheit / Mietverhältnis (docs/04 M3 page 3): tenancy timeline + create. */
export function UnitDetailPage({ accountId, unitId }: { accountId: string; unitId: string }) {
  const detail = useUnitDetail(accountId, unitId);

  if (detail.isPending) {
    return (
      <main className="px-8 py-10">
        <div aria-hidden="true" className="h-64 max-w-5xl animate-pulse rounded-xl bg-mint/60" />
      </main>
    );
  }
  if (detail.isError) {
    const missing = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <main className="px-8 py-10">
        <StatusNote
          kind="danger"
          label={missing ? 'Einheit nicht gefunden.' : 'Fehler beim Laden.'}
        >
          <Link className="underline underline-offset-4" href={`/a/${accountId}/objekte`}>
            Zurück zur Objektliste
          </Link>
        </StatusNote>
      </main>
    );
  }

  const unit = detail.data;
  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <p className="mb-1 text-sm">
          <Link
            href={`/a/${accountId}/objekte`}
            className="text-green underline-offset-4 hover:underline"
          >
            Objekte
          </Link>{' '}
          <span aria-hidden="true">/</span>{' '}
          <Link
            href={`/a/${accountId}/objekte/${unit.buildingId}`}
            className="text-green underline-offset-4 hover:underline"
          >
            {unit.buildingName}
          </Link>{' '}
          <span aria-hidden="true">/</span>
        </p>
        <h1 className="font-display text-3xl font-bold">{unit.label}</h1>
        <p className="mt-2 text-slate">
          {unit.areaSqm.toLocaleString('de-DE')} m² Wohnfläche · {unit.buildingName}
        </p>
      </header>

      <div className="grid max-w-5xl gap-8 lg:grid-cols-[2fr_1fr]">
        <section aria-label="Mietverhältnisse" className="flex flex-col gap-6">
          {unit.tenancies.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch kein Mietverhältnis</CardTitle>
                <CardDescription>
                  Legen Sie rechts das erste Mietverhältnis an. Zeiträume sind halboffen: das Ende
                  ist der erste Tag NACH dem Auszug.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Zeitstrahl</CardTitle>
                  <CardDescription>
                    Jeder Tag ist belegt: Mietverhältnis, Eigennutzung oder Leerstand. Zeiträume
                    sind halboffen (validFrom/validTo) — niemals einzelne Werte.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TenancyTimeline
                    tenancies={unit.tenancies}
                    selfUsePeriods={unit.selfUsePeriods}
                  />
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <Table>
                    <TableCaption>Mietverhältnisse in {unit.label}, neueste zuerst</TableCaption>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Mieter:in</TableHead>
                        <TableHead>Beginn</TableHead>
                        <TableHead>Ende (exkl.)</TableHead>
                        <TableHead className="text-right">Kaltmiete</TableHead>
                        <TableHead className="text-right">NK-Vorauszahlung</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {unit.tenancies.map((tenancy) => (
                        <TableRow key={tenancy.id}>
                          <TableCell className="font-semibold">
                            {tenancy.renterNames.join(', ')}
                            {tenancy.activeToday ? (
                              <span className="ml-2 rounded bg-success-tint px-1.5 py-0.5 text-xs font-semibold text-success">
                                aktiv
                              </span>
                            ) : null}
                          </TableCell>
                          <TableCell>{isoToGermanDate(tenancy.validFrom)}</TableCell>
                          <TableCell>
                            {tenancy.validTo ? isoToGermanDate(tenancy.validTo) : 'unbefristet'}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {tenancy.baseRentEur}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {tenancy.advancePaymentEur}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}

          {unit.selfUsePeriods.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Eigennutzung</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-slate">
                {unit.selfUsePeriods.map((s) => (
                  <p key={`${s.kind}-${s.validFrom}`}>
                    {s.kind === 'OWNER_OCCUPIED' ? 'Selbst bewohnt' : 'Unentgeltlich überlassen'} ·{' '}
                    {isoToGermanDate(s.validFrom)} –{' '}
                    {s.validTo ? isoToGermanDate(s.validTo) : 'offen'}
                  </p>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </section>

        <CreateTenancyForm accountId={accountId} unitId={unitId} />
      </div>
    </main>
  );
}

function CreateTenancyForm({ accountId, unitId }: { accountId: string; unitId: string }) {
  const create = useCreateTenancy(accountId, unitId);
  const form = useForm<TenancyForm>({
    resolver: zodResolver(TenancyFormSchema),
    defaultValues: EMPTY,
  });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.${unitId}.tenancy-create`, form);

  const onSubmit = form.handleSubmit((values) => {
    const baseRentCents = parseEurToCents(values.baseRent);
    const advancePaymentCents = parseEurToCents(values.advance);
    if (baseRentCents === null || advancePaymentCents === null) return;
    create.mutate(
      {
        renterName: values.renterName,
        validFrom: values.validFrom,
        validTo: values.validTo === '' ? null : values.validTo,
        baseRentCents,
        advancePaymentCents,
      },
      {
        onSuccess: () => {
          clearDraft();
          form.reset(EMPTY);
        },
      },
    );
  });

  const overlap = create.isError && create.error instanceof ApiError && create.error.status === 422;

  return (
    <section aria-label="Mietverhältnis anlegen">
      <Card>
        <CardHeader>
          <CardTitle>Mietverhältnis anlegen</CardTitle>
          <CardDescription>
            Eingaben werden automatisch als Entwurf gespeichert — nichts geht beim Abbrechen
            verloren. Einmal angelegt, ist ein Mietverhältnis unveränderlich; Korrekturen werden
            neue Versionen.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
            <FormField
              id="tenancy-renter"
              label="Mieter:in (voller Name)"
              error={form.formState.errors.renterName}
              registration={form.register('renterName')}
            />
            <FormField
              id="tenancy-from"
              label="Beginn"
              type="date"
              error={form.formState.errors.validFrom}
              registration={form.register('validFrom')}
            />
            <FormField
              id="tenancy-to"
              label="Ende (exklusiv, leer = unbefristet)"
              type="date"
              error={form.formState.errors.validTo}
              registration={form.register('validTo')}
            />
            <FormField
              id="tenancy-rent"
              label="Kaltmiete in € / Monat"
              hint="z. B. 950,00"
              inputMode="decimal"
              error={form.formState.errors.baseRent}
              registration={form.register('baseRent')}
            />
            <FormField
              id="tenancy-advance"
              label="NK-Vorauszahlung in € / Monat"
              hint="z. B. 220,00"
              inputMode="decimal"
              error={form.formState.errors.advance}
              registration={form.register('advance')}
            />
            <div>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Wird angelegt…' : 'Mietverhältnis anlegen'}
              </Button>
            </div>
            {draftRestored ? (
              <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
                Ihre letzten Eingaben wurden automatisch gesichert.
              </StatusNote>
            ) : null}
            {create.isError ? (
              <StatusNote kind="danger" label="Anlegen fehlgeschlagen.">
                {overlap
                  ? 'Der Zeitraum überschneidet sich mit einem bestehenden Mietverhältnis oder ist ungültig.'
                  : 'Bitte Eingaben prüfen und erneut versuchen.'}
              </StatusNote>
            ) : null}
            {create.isSuccess ? (
              <StatusNote kind="success" label="Gespeichert.">
                Das Mietverhältnis wurde angelegt.
              </StatusNote>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
