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
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { FormField } from '@/features/objekte/form-field';
import { ApiError } from '@/lib/api';
import { useFormDraft } from '@/lib/form-draft';
import { isoToGermanDate, parseEurToCents, parseMeterValueToX1000 } from '@/lib/format';

import { useCreateHeatingCost, useDeleteHeatingCost, useHeatingCosts } from './queries';

/**
 * Heizkosten (docs/04 M3 page 5, docs/06 Scenario 2).
 *
 * Deliberately NOT on the Kosten-erfassen page: a heating cost carries no
 * Umlageschlüssel, because §§ 7-9 HeizkostenV decide its split. Offering the
 * dropdown here would invite a legally wrong answer. The CO₂ figures sit on
 * the same row because they come off the same fuel invoice — suppliers must
 * state emissions and CO₂ price since 2023, and CO2KostAufG splits them.
 */

const HeatingCostFormSchema = z
  .object({
    label: z.string().min(1, 'Pflichtfeld'),
    amount: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((v) => parseEurToCents(v) !== null, 'Betrag wie 10.300,00 angeben')
      .refine((v) => (parseEurToCents(v) ?? 0) > 0, 'Betrag muss größer als 0 sein'),
    periodFrom: z.string().min(1, 'Pflichtfeld'),
    periodTo: z.string().min(1, 'Pflichtfeld'),
    co2Kg: z.string(),
    co2Cost: z.string(),
  })
  .refine((v) => v.periodTo > v.periodFrom, {
    path: ['periodTo'],
    message: 'Ende muss nach dem Beginn liegen',
  })
  .refine((v) => v.co2Kg === '' || parseMeterValueToX1000(v.co2Kg) !== null, {
    path: ['co2Kg'],
    message: 'Menge wie 2.000 angeben',
  })
  .refine((v) => v.co2Cost === '' || parseEurToCents(v.co2Cost) !== null, {
    path: ['co2Cost'],
    message: 'Betrag wie 300,00 angeben',
  })
  .refine((v) => (v.co2Kg === '') === (v.co2Cost === ''), {
    path: ['co2Cost'],
    // Without both there is nothing to grade or nothing to split — a half-
    // filled CO₂ block would silently drop the whole CO2KostAufG step.
    message: 'CO₂-Menge und CO₂-Kosten immer gemeinsam angeben',
  });
type HeatingCostForm = z.infer<typeof HeatingCostFormSchema>;

const EMPTY: HeatingCostForm = {
  label: '',
  amount: '',
  periodFrom: '2025-01-01',
  periodTo: '2026-01-01',
  co2Kg: '',
  co2Cost: '',
};

export function HeatingCostSection({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const heatingCosts = useHeatingCosts(accountId, buildingId);
  const [formOpen, setFormOpen] = useState(false);

  return (
    <section aria-labelledby="heating-costs-heading">
      <Card>
        <CardHeader>
          <CardTitle id="heating-costs-heading">Heizkosten des Gebäudes</CardTitle>
          <CardDescription>
            Rechnung des Energieversorgers inkl. CO₂-Menge und CO₂-Kosten. Diese Kosten tragen
            keinen Umlageschlüssel — sie werden nach §§ 7–9 HeizkostenV auf Grund- und
            Verbrauchskosten aufgeteilt.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {heatingCosts.isPending ? (
            <div aria-hidden="true" className="h-24 animate-pulse rounded-lg bg-mint/60" />
          ) : heatingCosts.isError ? (
            <StatusNote kind="danger" label="Heizkosten konnten nicht geladen werden.">
              Bitte erneut versuchen.
            </StatusNote>
          ) : heatingCosts.data.heatingCosts.length === 0 ? (
            <StatusNote kind="warning" label="Noch keine Heizkosten erfasst.">
              Ohne die Rechnung des Energieversorgers kann keine Heizkostenabrechnung erstellt
              werden.
            </StatusNote>
          ) : (
            <Table>
              <TableCaption>
                Erfasste Heizkosten. Der CO₂-Anteil ist im Gesamtbetrag enthalten und wird vor der
                Umlage nach CO2KostAufG zwischen Vermieter und Mieter geteilt.
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>Position</TableHead>
                  <TableHead className="text-right">Betrag</TableHead>
                  <TableHead>Zeitraum</TableHead>
                  <TableHead className="text-right">CO₂-Menge</TableHead>
                  <TableHead className="text-right">CO₂-Kosten</TableHead>
                  <TableHead>
                    <span className="sr-only">Aktion</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {heatingCosts.data.heatingCosts.map((cost) => (
                  <HeatingCostRow
                    key={cost.id}
                    accountId={accountId}
                    buildingId={buildingId}
                    cost={cost}
                  />
                ))}
              </TableBody>
            </Table>
          )}

          {formOpen ? (
            <HeatingCostForm
              accountId={accountId}
              buildingId={buildingId}
              onDone={() => setFormOpen(false)}
            />
          ) : (
            <div>
              <Button variant="outline" onClick={() => setFormOpen(true)}>
                Heizkosten erfassen
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function HeatingCostRow({
  accountId,
  buildingId,
  cost,
}: {
  accountId: string;
  buildingId: string;
  cost: {
    id: string;
    label: string;
    amountEur: string;
    periodFrom: string;
    periodTo: string;
    co2KgDisplay: string | null;
    co2CostEur: string | null;
  };
}) {
  const remove = useDeleteHeatingCost(accountId, buildingId);
  const [confirming, setConfirming] = useState(false);
  return (
    <TableRow>
      <TableCell className="font-semibold">{cost.label}</TableCell>
      <TableCell className="text-right tabular-nums">{cost.amountEur}</TableCell>
      <TableCell className="text-sm text-slate">
        {isoToGermanDate(cost.periodFrom)} – {isoToGermanDate(cost.periodTo)}
      </TableCell>
      <TableCell className="text-right tabular-nums">
        {cost.co2KgDisplay ? `${cost.co2KgDisplay} kg` : '—'}
      </TableCell>
      <TableCell className="text-right tabular-nums">{cost.co2CostEur ?? '—'}</TableCell>
      <TableCell>
        {confirming ? (
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
              <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
                Abbrechen
              </Button>
            </div>
          </div>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="text-danger hover:bg-danger-tint"
            onClick={() => setConfirming(true)}
          >
            Löschen
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}

function HeatingCostForm({
  accountId,
  buildingId,
  onDone,
}: {
  accountId: string;
  buildingId: string;
  onDone: () => void;
}) {
  const create = useCreateHeatingCost(accountId, buildingId);
  const form = useForm<HeatingCostForm>({
    resolver: zodResolver(HeatingCostFormSchema),
    defaultValues: EMPTY,
  });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${buildingId}.heating-cost-create`,
    form,
  );

  const onSubmit = form.handleSubmit((values) => {
    const amountCents = parseEurToCents(values.amount);
    if (amountCents === null) return; // zod already guards this
    create.mutate(
      {
        label: values.label,
        amountCents,
        periodFrom: values.periodFrom,
        periodTo: values.periodTo,
        co2KgX1000: values.co2Kg ? parseMeterValueToX1000(values.co2Kg) : null,
        co2CostCents: values.co2Cost ? parseEurToCents(values.co2Cost) : null,
      },
      {
        onSuccess: () => {
          clearDraft();
          form.reset(EMPTY);
          onDone();
        },
      },
    );
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4 border-t border-mint pt-5">
      <h3 className="font-display text-base font-bold">Heizkosten erfassen</h3>
      <FormField
        id="heating-label"
        label="Position"
        hint="z. B. Heizung & Warmwasser (Brennstoff, Wartung, Betriebsstrom)"
        error={form.formState.errors.label}
        registration={form.register('label')}
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <FormField
          id="heating-amount"
          label="Gesamtbetrag in €"
          hint="inkl. CO₂-Anteil"
          inputMode="decimal"
          error={form.formState.errors.amount}
          registration={form.register('amount')}
        />
        <FormField
          id="heating-from"
          label="Zeitraum von"
          type="date"
          error={form.formState.errors.periodFrom}
          registration={form.register('periodFrom')}
        />
        <FormField
          id="heating-to"
          label="bis (exklusiv)"
          type="date"
          error={form.formState.errors.periodTo}
          registration={form.register('periodTo')}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id="heating-co2-kg"
          label="CO₂-Menge in kg (optional)"
          hint="steht auf der Rechnung des Versorgers"
          inputMode="decimal"
          error={form.formState.errors.co2Kg}
          registration={form.register('co2Kg')}
        />
        <FormField
          id="heating-co2-cost"
          label="CO₂-Kosten in € (optional)"
          hint="im Gesamtbetrag enthalten"
          inputMode="decimal"
          error={form.formState.errors.co2Cost}
          registration={form.register('co2Cost')}
        />
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Wird erfasst…' : 'Heizkosten erfassen'}
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Abbrechen
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
            ? 'Bitte Zeitraum und Beträge prüfen — die CO₂-Kosten dürfen den Gesamtbetrag nicht übersteigen.'
            : 'Bitte erneut versuchen.'}
        </StatusNote>
      ) : null}
    </form>
  );
}
