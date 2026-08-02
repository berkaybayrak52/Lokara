'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Label, Select, StatusNote } from '@lokara/ui';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { FormField } from '@/features/objekte/form-field';
import { ApiError } from '@/lib/api';
import type { MeterOut } from '@/lib/contracts';
import { READING_REASONS, READING_REASON_LABELS } from '@/lib/contracts';
import { useFormDraft } from '@/lib/form-draft';
import { parseMeterValueToX1000 } from '@/lib/format';

import { useCreateReading } from './queries';

const ReadingFormSchema = z.object({
  readAt: z.string().min(1, 'Pflichtfeld'),
  value: z
    .string()
    .min(1, 'Pflichtfeld')
    .refine((v) => parseMeterValueToX1000(v) !== null, 'Zählerstand wie 1.800 oder 241,5 angeben'),
  reason: z.enum(READING_REASONS),
  note: z.string(),
});
type ReadingForm = z.infer<typeof ReadingFormSchema>;

const EMPTY: ReadingForm = {
  readAt: '2025-12-31',
  value: '',
  reason: 'PERIODIC',
  note: '',
};

/**
 * Ablesung erfassen — the only write path a reading has.
 *
 * There is no edit button anywhere for a reading, and that is the feature: to
 * fix a value you record a new one for the same date with Grund "Korrektur",
 * and it supersedes the old one for billing while both stay on file.
 */
export function CreateReadingForm({
  accountId,
  buildingId,
  meter,
}: {
  accountId: string;
  buildingId: string;
  meter: MeterOut;
}) {
  const create = useCreateReading(accountId, buildingId);
  const form = useForm<ReadingForm>({
    resolver: zodResolver(ReadingFormSchema),
    defaultValues: EMPTY,
  });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${meter.id}.reading-create`,
    form,
  );

  const onSubmit = form.handleSubmit((values) => {
    const valueX1000 = parseMeterValueToX1000(values.value);
    if (valueX1000 === null) return; // zod already guards this
    create.mutate(
      {
        meterId: meter.id,
        readAt: values.readAt,
        valueX1000,
        reason: values.reason,
        note: values.note.trim() || null,
      },
      {
        onSuccess: () => {
          clearDraft();
          form.reset(EMPTY);
        },
      },
    );
  });

  const reasonId = `reason-${meter.id}`;
  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      <h3 className="font-display text-base font-bold">Ablesung erfassen</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id={`read-at-${meter.id}`}
          label="Ablesedatum"
          type="date"
          error={form.formState.errors.readAt}
          registration={form.register('readAt')}
        />
        <FormField
          id={`value-${meter.id}`}
          label={`Zählerstand in ${meter.unitSymbol}`}
          hint="Ablesewert, nicht der Verbrauch"
          inputMode="decimal"
          error={form.formState.errors.value}
          registration={form.register('value')}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={reasonId}>Ablesegrund</Label>
        <Select id={reasonId} {...form.register('reason')}>
          {READING_REASONS.map((reason) => (
            <option key={reason} value={reason}>
              {READING_REASON_LABELS[reason]}
            </option>
          ))}
        </Select>
        <p className="text-sm text-slate">
          Falscher Wert erfasst? Mit „Korrektur“ denselben Tag neu ablesen — der alte Eintrag bleibt
          sichtbar und wird abgelöst.
        </p>
      </div>
      <FormField
        id={`note-${meter.id}`}
        label="Notiz (optional)"
        error={undefined}
        registration={form.register('note')}
      />
      <div>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Wird erfasst…' : 'Ablesung erfassen'}
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
            ? 'Bitte Datum und Zählerstand prüfen.'
            : 'Bitte erneut versuchen.'}
        </StatusNote>
      ) : null}
      {create.isSuccess ? (
        <StatusNote kind="success" label="Ablesung gespeichert.">
          Verbrauch im Zeitraum:{' '}
          {create.data.periodConsumptionDisplay ?? 'noch kein vollständiges Ablesepaar'}. Die
          Abrechnung rechnet damit neu.
        </StatusNote>
      ) : null}
    </form>
  );
}
