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
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';
import { useForm } from 'react-hook-form';

import {
  CostFormSchema,
  EMPTY_COST_FORM,
  toCostCreateInput,
  type CostForm,
} from '@/features/kosten/cost-form';
import { useCreateCost } from '@/features/kosten/queries';
import { FormField } from '@/features/objekte/form-field';
import { ApiError } from '@/lib/api';
import { ALLOCATION_KEYS, ALLOCATION_KEY_LABELS, type ExtractionResponse } from '@/lib/contracts';
import { centsToEurInput } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { ConfidenceBadge } from './confidence-badge';
import { reviewDraftKey } from './queries';

/**
 * Step 2: the human gate. Nothing has been written at this point — the fields
 * are a proposal, the form below is the ordinary cost-entry form prefilled
 * with them, and only "Kostenart übernehmen" creates the entry.
 */
export function ReviewStep({
  accountId,
  buildingId,
  extraction,
  restored,
  units,
  onConfirmed,
  onDiscard,
}: {
  accountId: string;
  buildingId: string;
  extraction: ExtractionResponse;
  restored: boolean;
  units: { id: string; label: string }[];
  /** Receives the label that was actually stored — the corrected one, if the
   * reviewer changed it. */
  onConfirmed: (label: string) => void;
  onDiscard: () => void;
}) {
  const create = useCreateCost(accountId, buildingId);
  const prefilled: CostForm = {
    ...EMPTY_COST_FORM,
    label: extraction.prefill.label,
    amount: centsToEurInput(extraction.prefill.amountCents),
    periodFrom: extraction.prefill.periodFrom,
    periodTo: extraction.prefill.periodTo,
    key: extraction.prefill.key,
  };
  const form = useForm<CostForm>({
    resolver: zodResolver(CostFormSchema),
    defaultValues: prefilled,
  });
  const { draftRestored, clearDraft } = useFormDraft(reviewDraftKey(accountId, buildingId), form);
  const selectedKey = form.watch('key');

  const onSubmit = form.handleSubmit((values) => {
    const input = toCostCreateInput(values);
    if (input === null) return; // zod already guards this
    create.mutate(input, {
      onSuccess: (cost) => {
        clearDraft();
        onConfirmed(cost.label);
      },
    });
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[3fr_2fr]">
      <section aria-label="Erkannte Felder">
        <Card>
          <CardHeader>
            <CardTitle>Erkannte Felder</CardTitle>
            <CardDescription>
              {extraction.documentName} · Lesequalität {extraction.documentConfidencePercent} %.
              Prüfen Sie die markierten Werte und korrigieren Sie rechts, bevor Sie übernehmen.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feld</TableHead>
                  <TableHead>Erkannter Wert</TableHead>
                  <TableHead>Sicherheit</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {extraction.fields.map((field) => (
                  <TableRow key={field.id}>
                    <TableCell className="align-top font-semibold">{field.label}</TableCell>
                    <TableCell className="align-top">
                      <span className={field.stored ? '' : 'text-slate'}>{field.value}</span>
                      {field.note ? (
                        <p className="mt-1 max-w-prose text-xs text-slate">{field.note}</p>
                      ) : null}
                    </TableCell>
                    <TableCell className="align-top">
                      <ConfidenceBadge
                        percent={field.confidencePercent}
                        needsReview={field.needsReview}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="rounded-lg bg-paper px-4 py-3">
              <p className="text-sm font-semibold">Nicht aus dem Beleg gelesen</p>
              <p className="mt-1 text-sm text-slate">
                {extraction.notExtracted.join(' · ')} — die Vorbelegung rechts entspricht der
                normalen Eingabemaske, nicht dem Dokument. Bitte bewusst wählen.
              </p>
            </div>

            {extraction.duplicate ? (
              <StatusNote kind="warning" label="Möglicherweise bereits erfasst.">
                {extraction.duplicate.label} über {extraction.duplicate.amountEur} liegt für diesen
                Zeitraum schon vor. Doppelte Erfassung würde die Abrechnung verdoppeln — prüfen Sie
                das unter{' '}
                <Link
                  href={`/a/${accountId}/kosten`}
                  className="text-warning underline underline-offset-4"
                >
                  Kosten erfassen
                </Link>
                .
              </StatusNote>
            ) : null}
            {restored ? (
              <StatusNote kind="warning" label="Prüfung wiederhergestellt.">
                Der zuletzt ausgelesene Beleg wurde weiterhin nicht gespeichert.
              </StatusNote>
            ) : null}

            <p className="text-sm text-slate">{extraction.providerLabel}</p>
          </CardContent>
        </Card>
      </section>

      <section aria-label="Kostenart prüfen und übernehmen">
        <Card>
          <CardHeader>
            <CardTitle>Prüfen und übernehmen</CardTitle>
            <CardDescription>
              Vorbelegt aus dem Beleg, vollständig änderbar. Erst mit „Kostenart übernehmen" wird
              gespeichert — Ihre Korrekturen werden bis dahin automatisch als Entwurf gesichert.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
              <FormField
                id="beleg-label"
                label="Kostenart"
                hint="Aus dem Beleg abgeleitet — bitte prüfen"
                error={form.formState.errors.label}
                registration={form.register('label')}
              />
              <FormField
                id="beleg-amount"
                label="Betrag in € (Gesamtkosten)"
                hint="z. B. 1.200,00"
                inputMode="decimal"
                error={form.formState.errors.amount}
                registration={form.register('amount')}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  id="beleg-from"
                  label="Zeitraum von"
                  type="date"
                  error={form.formState.errors.periodFrom}
                  registration={form.register('periodFrom')}
                />
                <FormField
                  id="beleg-to"
                  label="bis (exklusiv)"
                  type="date"
                  error={form.formState.errors.periodTo}
                  registration={form.register('periodTo')}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="beleg-key">Umlageschlüssel</Label>
                <Select id="beleg-key" {...form.register('key')}>
                  {ALLOCATION_KEYS.map((key) => (
                    <option key={key} value={key} disabled={key === 'DIRECT' && units.length === 0}>
                      {ALLOCATION_KEY_LABELS[key]}
                    </option>
                  ))}
                </Select>
                <p className="text-sm text-slate">
                  Nicht aus dem Beleg — später jederzeit änderbar, ohne Datenverlust.
                </p>
              </div>
              {selectedKey === 'DIRECT' ? (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="beleg-direct-unit">Direkt zuordnen an</Label>
                  <Select
                    id="beleg-direct-unit"
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
              <div className="flex gap-2">
                <Button type="submit" disabled={create.isPending}>
                  {create.isPending ? 'Wird übernommen…' : 'Kostenart übernehmen'}
                </Button>
                <Button type="button" variant="ghost" onClick={onDiscard}>
                  Verwerfen
                </Button>
              </div>
              {draftRestored ? (
                <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
                  Ihre letzten Korrekturen wurden automatisch gesichert.
                </StatusNote>
              ) : null}
              {create.isError ? (
                <StatusNote kind="danger" label="Übernehmen fehlgeschlagen.">
                  {create.error instanceof ApiError && create.error.status === 422
                    ? 'Bitte Zeitraum und Umlageschlüssel prüfen.'
                    : 'Bitte erneut versuchen.'}
                </StatusNote>
              ) : null}
            </form>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
