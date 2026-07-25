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
} from '@lokara/ui';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { FormField } from '@/features/objekte/form-field';
import { ApiError } from '@/lib/api';
import {
  MEASUREMENT_UNIT_LABELS,
  METER_KINDS,
  METER_KIND_LABELS,
  UNITS_BY_KIND,
} from '@/lib/contracts';
import { useFormDraft } from '@/lib/form-draft';

import { useCreateMeter } from './queries';

const MeterFormSchema = z.object({
  kind: z.enum(METER_KINDS),
  measurementUnit: z.enum(['KWH', 'CUBIC_METRE', 'HKV_UNITS']),
  serial: z.string().min(1, 'Pflichtfeld'),
  unitId: z.string(),
  label: z.string(),
  calibrationValidUntil: z.string(),
});
type MeterForm = z.infer<typeof MeterFormSchema>;

const EMPTY: MeterForm = {
  kind: 'HEAT',
  measurementUnit: 'HKV_UNITS',
  serial: '',
  unitId: '',
  label: '',
  calibrationValidUntil: '',
};

export function CreateMeterForm({
  accountId,
  buildingId,
  units,
}: {
  accountId: string;
  buildingId: string;
  units: { id: string; label: string }[];
}) {
  const create = useCreateMeter(accountId, buildingId);
  const form = useForm<MeterForm>({
    resolver: zodResolver(MeterFormSchema),
    defaultValues: EMPTY,
  });
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${buildingId}.meter-create`,
    form,
  );
  const kind = form.watch('kind');
  const measurementUnit = form.watch('measurementUnit');
  const allowedUnits = UNITS_BY_KIND[kind];

  // Water is always m³ and only heat may count kWh or HKV units — mirroring
  // the API's validator here means the impossible combination is never even
  // offered, instead of being rejected after the fact.
  useEffect(() => {
    if (!allowedUnits.includes(measurementUnit)) {
      form.setValue('measurementUnit', allowedUnits[0]!);
    }
  }, [allowedUnits, measurementUnit, form]);

  const onSubmit = form.handleSubmit((values) => {
    create.mutate(
      {
        kind: values.kind,
        measurementUnit: values.measurementUnit,
        serial: values.serial,
        unitId: values.unitId || null,
        label: values.label.trim() || null,
        calibrationValidUntil: values.calibrationValidUntil || null,
      },
      {
        onSuccess: () => {
          clearDraft();
          form.reset(EMPTY);
        },
      },
    );
  });

  return (
    <section aria-label="Zähler anlegen">
      <Card>
        <CardHeader>
          <CardTitle>Zähler anlegen</CardTitle>
          <CardDescription>
            Eingaben werden automatisch als Entwurf gespeichert — nichts geht beim Abbrechen
            verloren.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="meter-kind">Zählerart</Label>
              <Select id="meter-kind" {...form.register('kind')}>
                {METER_KINDS.map((value) => (
                  <option key={value} value={value}>
                    {METER_KIND_LABELS[value]}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="meter-unit">Zähleinheit</Label>
              <Select id="meter-unit" {...form.register('measurementUnit')}>
                {allowedUnits.map((value) => (
                  <option key={value} value={value}>
                    {MEASUREMENT_UNIT_LABELS[value]}
                  </option>
                ))}
              </Select>
              <p className="text-sm text-slate">
                {kind === 'HEAT'
                  ? 'kWh nur für den Wärmemengenzähler der Heizzentrale — er liefert die Energiemenge nach § 9 HeizkostenV.'
                  : 'Wasser wird immer in m³ gezählt.'}
              </p>
            </div>
            <FormField
              id="meter-serial"
              label="Zählernummer"
              hint="wie auf dem Gerät aufgedruckt"
              error={form.formState.errors.serial}
              registration={form.register('serial')}
            />
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="meter-location">Einbauort</Label>
              <Select id="meter-location" {...form.register('unitId')}>
                <option value="">Gebäude (Hauptzähler)</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.label}
                  </option>
                ))}
              </Select>
            </div>
            <FormField
              id="meter-calibration"
              label="Eichfrist bis (optional)"
              hint="Heizkostenverteiler sind nicht eichpflichtig — dann leer lassen."
              type="date"
              error={undefined}
              registration={form.register('calibrationValidUntil')}
            />
            <div>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Wird angelegt…' : 'Zähler anlegen'}
              </Button>
            </div>
            {draftRestored ? (
              <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
                Ihre letzten Eingaben wurden automatisch gesichert.
              </StatusNote>
            ) : null}
            {create.isError ? (
              <StatusNote kind="danger" label="Anlegen fehlgeschlagen.">
                {create.error instanceof ApiError && create.error.status === 422
                  ? 'Bitte Zählernummer und Zähleinheit prüfen — die Nummer muss im Objekt eindeutig sein.'
                  : 'Bitte erneut versuchen.'}
              </StatusNote>
            ) : null}
            {create.isSuccess ? (
              <StatusNote kind="success" label="Zähler angelegt.">
                Erfassen Sie jetzt Anfangs- und Endstand für den Abrechnungszeitraum.
              </StatusNote>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
