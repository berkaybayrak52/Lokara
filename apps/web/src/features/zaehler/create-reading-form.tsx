'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Label, Select, StatusNote } from '@lokara/ui';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { FormField } from '@/features/objekte/form-field';
import { ApiError } from '@/lib/api';
import type { MeterOut } from '@/lib/contracts';
import { READING_REASON_LABELS } from '@/lib/contracts';
import { useFormDraft } from '@/lib/form-draft';
import { parseMeterValueToX1000 } from '@/lib/format';

import type { ReadingCreateInput } from './queries';
import { useCheckReading, useCreateReading } from './queries';

const ALLOWED_REASONS = ['PERIODIC', 'INTERIM', 'TENANT_CHANGE', 'CORRECTION'] as const;

function todayInput(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

const ReadingFormSchema = z
  .object({
    readAt: z.string().min(1, 'Pflichtfeld'),
    value: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((value) => parseMeterValueToX1000(value) !== null, 'Stand wie 1.800 oder 241,5'),
    reason: z.enum(ALLOWED_REASONS),
    note: z.string(),
    correctionTargetId: z.string(),
    correctionReason: z.string(),
  })
  .superRefine((value, context) => {
    if (value.reason === 'CORRECTION' && !value.correctionTargetId) {
      context.addIssue({
        code: 'custom',
        path: ['correctionTargetId'],
        message: 'Zu korrigierende Ablesung auswählen',
      });
    }
    if (value.reason === 'CORRECTION' && !value.correctionReason.trim()) {
      context.addIssue({
        code: 'custom',
        path: ['correctionReason'],
        message: 'Begründung ist erforderlich',
      });
    }
  });
type ReadingForm = z.infer<typeof ReadingFormSchema>;

export function CreateReadingForm({
  accountId,
  buildingId,
  meter,
}: {
  accountId: string;
  buildingId: string;
  meter: MeterOut;
}) {
  const check = useCheckReading(accountId);
  const create = useCreateReading(accountId, buildingId);
  const [pending, setPending] = useState<ReadingCreateInput | null>(null);
  const form = useForm<ReadingForm>({
    resolver: zodResolver(ReadingFormSchema),
    defaultValues: {
      readAt: todayInput(),
      value: '',
      reason: 'PERIODIC',
      note: '',
      correctionTargetId: '',
      correctionReason: '',
    },
  });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${meter.id}.reading-create`,
    form,
  );
  const reason = form.watch('reason');

  function save(input: ReadingCreateInput) {
    create.mutate(input, {
      onSuccess: () => {
        clearDraft();
        setPending(null);
        check.reset();
        form.reset({
          readAt: todayInput(),
          value: '',
          reason: 'PERIODIC',
          note: '',
          correctionTargetId: '',
          correctionReason: '',
        });
      },
    });
  }

  const onSubmit = form.handleSubmit((values) => {
    const valueX1000 = parseMeterValueToX1000(values.value);
    if (valueX1000 === null) return;
    const input: ReadingCreateInput = {
      meterId: meter.id,
      readAt: values.readAt,
      valueX1000,
      reason: values.reason,
      note: values.note.trim() || null,
      supersedesReadingId: values.reason === 'CORRECTION' ? values.correctionTargetId : null,
      confirmationNote: values.reason === 'CORRECTION' ? values.correctionReason.trim() : null,
    };
    check.mutate(input, {
      onSuccess: (result) => {
        if (result.findings.some((finding) => finding.severity === 'BLOCKER')) return;
        const confirmations = result.findings.filter((finding) => finding.requiresConfirmation);
        if (confirmations.length > 0) {
          setPending(input);
          return;
        }
        save(input);
      },
    });
  });

  const effectiveReadings = meter.readings.filter((reading) => !reading.superseded);

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      <div>
        <h3 className="font-display text-base font-bold">Ablesung erfassen</h3>
        <p className="mt-1 text-sm text-slate">
          {meter.deviceTypeLabel} · Nr. {meter.serial} · letzte wirksame Ablesung:{' '}
          {effectiveReadings[0]
            ? `${effectiveReadings[0].valueDisplay} ${meter.unitSymbol} am ${new Intl.DateTimeFormat('de-DE').format(new Date(`${effectiveReadings[0].readAt}T12:00:00`))}`
            : 'noch keine'}
        </p>
        <p className="mt-1 text-xs text-slate">Quelle: Manuell erfasst</p>
      </div>
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
        <Label htmlFor={`reason-${meter.id}`}>Ablesegrund</Label>
        <Select id={`reason-${meter.id}`} {...form.register('reason')}>
          {ALLOWED_REASONS.map((value) => (
            <option key={value} value={value}>
              {READING_REASON_LABELS[value]}
            </option>
          ))}
        </Select>
        <p className="text-sm text-slate">
          Ein Gerätewechsel wird über „Zähler ersetzen“ durchgeführt, damit beide Geräte und Stände
          verbunden bleiben.
        </p>
      </div>
      {reason === 'CORRECTION' ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`correction-target-${meter.id}`}>Zu korrigierende Ablesung</Label>
            <Select id={`correction-target-${meter.id}`} {...form.register('correctionTargetId')}>
              <option value="">Bitte auswählen</option>
              {effectiveReadings.map((reading) => (
                <option key={reading.id} value={reading.id}>
                  {reading.readAt} · {reading.valueDisplay} {meter.unitSymbol}
                </option>
              ))}
            </Select>
            {form.formState.errors.correctionTargetId ? (
              <p className="text-sm text-danger">
                {form.formState.errors.correctionTargetId.message}
              </p>
            ) : null}
          </div>
          <FormField
            id={`correction-reason-${meter.id}`}
            label="Korrekturgrund"
            error={form.formState.errors.correctionReason}
            registration={form.register('correctionReason')}
          />
        </div>
      ) : null}
      <FormField
        id={`note-${meter.id}`}
        label="Notiz (optional)"
        error={undefined}
        registration={form.register('note')}
      />
      <div>
        <Button type="submit" disabled={check.isPending || create.isPending}>
          {check.isPending
            ? 'Wird geprüft…'
            : create.isPending
              ? 'Wird erfasst…'
              : 'Ablesung prüfen'}
        </Button>
      </div>
      {draftRestored ? (
        <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
          Ihre letzten Eingaben wurden automatisch gesichert.
        </StatusNote>
      ) : null}
      {check.data?.findings.map((finding) => (
        <StatusNote
          key={finding.code}
          kind={finding.severity === 'BLOCKER' ? 'danger' : 'warning'}
          label={finding.severity === 'BLOCKER' ? 'Speichern nicht möglich.' : 'Bitte prüfen.'}
        >
          {finding.message}
        </StatusNote>
      ))}
      {pending ? (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-warning bg-warning-tint p-4">
          <p className="text-sm text-ink">Die Hinweise wurden gelesen und der Stand ist korrekt.</p>
          <Button
            type="button"
            size="sm"
            disabled={create.isPending}
            onClick={() =>
              save({
                ...pending,
                confirmedFindingCodes:
                  check.data?.findings
                    .filter((finding) => finding.requiresConfirmation)
                    .map((finding) => finding.code) ?? [],
              })
            }
          >
            Trotzdem speichern
          </Button>
        </div>
      ) : null}
      {check.isError || create.isError ? (
        <StatusNote kind="danger" label="Erfassen fehlgeschlagen.">
          {(check.error instanceof ApiError && check.error.detail) ||
            (create.error instanceof ApiError && create.error.detail) ||
            'Bitte erneut versuchen.'}
        </StatusNote>
      ) : null}
      {create.isSuccess ? (
        <StatusNote kind="success" label="Ablesung gespeichert.">
          Die wirksame Historie und der Verbrauch wurden neu projiziert.
        </StatusNote>
      ) : null}
    </form>
  );
}
