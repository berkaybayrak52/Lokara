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
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { ApiError } from '@/lib/api';
import type { TenancyOut } from '@/lib/contracts';
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
    // Freie Herkunftsangabe (kein rechenrelevanter Betrag); leer → Default beim Senden.
    declarationRef: z.string(),
  })
  .refine((values) => values.validTo === '' || values.validTo > values.validFrom, {
    path: ['validTo'],
    message: 'Ende muss nach dem Beginn liegen',
  });
type TenancyForm = z.infer<typeof TenancyFormSchema>;

const EMPTY: TenancyForm = {
  renterName: '',
  validFrom: '',
  validTo: '',
  baseRent: '',
  advance: '',
  declarationRef: 'Mietvertrag',
};

/**
 * NK-Vorauszahlung zur Anzeige: die heute gültige Periode (validFrom ≤ heute und
 * validTo leer oder nach heute), sonst die zeitlich letzte; leere Liste → „—".
 */
function advanceEurToday(schedule: TenancyOut['advancePaymentSchedule']): string {
  if (schedule.length === 0) return '—';
  const today = new Date().toISOString().slice(0, 10);
  const current = schedule.find(
    (period) => period.validFrom <= today && (period.validTo === null || period.validTo > today),
  );
  const chosen =
    current ?? [...schedule].sort((a, b) => (a.validFrom < b.validFrom ? 1 : -1))[0];
  return chosen?.amountEur ?? '—';
}

/** Einheit / Mietverhältnis (docs/04 M3 page 3): tenancy timeline + create. */
export function UnitDetailPage({ accountId, unitId }: { accountId: string; unitId: string }) {
  const detail = useUnitDetail(accountId, unitId);

  if (detail.isPending) {
    return (
      <main className="py-10">
        <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-mint/60" />
      </main>
    );
  }
  if (detail.isError) {
    const missing = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <main className="py-10">
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
    <main className="py-10">
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

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
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
                            {advanceEurToday(tenancy.advancePaymentSchedule)}
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

        <TenancyEntry accountId={accountId} unitId={unitId} />
      </div>
    </main>
  );
}

/**
 * Einstieg „Jetzt Mietverhältnis erstellen" (O11): erst die Wahl zwischen
 * Vertragsgenerator (externe Route, entsteht parallel) und manuellem Einpflegen;
 * „selbst einpflegen" blendet das bestehende Formular auf derselben Seite auf.
 */
function TenancyEntry({ accountId, unitId }: { accountId: string; unitId: string }) {
  const [mode, setMode] = useState<'idle' | 'choosing' | 'manual'>('idle');

  if (mode === 'manual') {
    return <CreateTenancyForm accountId={accountId} unitId={unitId} />;
  }

  return (
    <section aria-label="Mietverhältnis erstellen">
      <Card>
        <CardHeader>
          <CardTitle>Mietverhältnis</CardTitle>
          <CardDescription>
            Mit dem Vertragsgenerator erzeugen und Daten automatisch übernehmen, oder bestehende
            Angaben selbst einpflegen.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mode === 'idle' ? (
            <Button onClick={() => setMode('choosing')}>Jetzt Mietverhältnis erstellen</Button>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <Link
                href={`/a/${accountId}/vertraege/neu?unitId=${unitId}`}
                className="flex flex-col rounded-xl border border-mint p-4 transition-colors hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <span className="font-semibold text-ink">Mit Vertragsgenerator</span>
                <span className="mt-1 text-sm text-slate">
                  Vertrag erzeugen und Daten automatisch übernehmen.
                </span>
              </Link>
              <button
                type="button"
                onClick={() => setMode('manual')}
                className="flex flex-col rounded-xl border border-mint p-4 text-left transition-colors hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <span className="font-semibold text-ink">Vertragsdaten selbst einpflegen</span>
                <span className="mt-1 text-sm text-slate">Bestehende Angaben manuell erfassen.</span>
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
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
    const initialAdvancePaymentCents = parseEurToCents(values.advance);
    if (baseRentCents === null || initialAdvancePaymentCents === null) return;
    create.mutate(
      {
        renterName: values.renterName,
        validFrom: values.validFrom,
        validTo: values.validTo === '' ? null : values.validTo,
        baseRentCents,
        initialAdvancePaymentCents,
        advanceDeclarationRef: values.declarationRef.trim() || 'Mietvertrag',
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
            <FormField
              id="tenancy-declaration"
              label="Grundlage der NK-Vorauszahlung"
              hint="z. B. Mietvertrag"
              error={form.formState.errors.declarationRef}
              registration={form.register('declarationRef')}
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
