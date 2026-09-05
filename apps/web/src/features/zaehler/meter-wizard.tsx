'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Label,
  Select,
  StatusNote,
} from '@lokara/ui';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { FormField } from '@/features/objekte/form-field';
import { PageHeader } from '@/features/portal/page-header';
import { ApiError } from '@/lib/api';
import {
  DEVICE_TYPE_UNIT,
  MEASUREMENT_UNIT_LABELS,
  METER_DEVICE_TYPES,
  METER_DEVICE_TYPE_LABELS,
} from '@/lib/contracts';
import { useFormDraft } from '@/lib/form-draft';
import { parseMeterValueToX1000 } from '@/lib/format';

import { useCreateMeter, useMeterWorkspace } from './queries';

const FormSchema = z
  .object({
    buildingId: z.string().min(1, 'Objekt auswählen'),
    assignment: z.enum(['BUILDING', 'UNIT']),
    unitId: z.string(),
    deviceType: z.enum(METER_DEVICE_TYPES),
    serial: z.string().min(1, 'Pflichtfeld'),
    label: z.string(),
    location: z.string(),
    manufacturer: z.string(),
    model: z.string(),
    installedOn: z.string().min(1, 'Pflichtfeld'),
    remoteReadability: z.enum(['REMOTE_READABLE', 'NOT_REMOTE_READABLE', 'UNKNOWN']),
    calibrationDataState: z.enum([
      'DATA_AVAILABLE',
      'MISSING_DATA',
      'NOT_APPLICABLE',
      'REVIEW_REQUIRED',
    ]),
    calibrationDate: z.string(),
    calibrationEvidenceRef: z.string(),
    valuationFactor: z.string(),
    creationMode: z.enum(['NEW', 'EXISTING', 'REPLACEMENT']),
    replacesMeterId: z.string(),
    oldFinalValue: z.string(),
    newInitialValue: z.string(),
    replacementReason: z.string(),
    gasCalorificFactor: z.string(),
    gasConditionNumber: z.string(),
    gasValidFrom: z.string(),
    gasValidTo: z.string(),
    gasSupplierInvoiceReference: z.string(),
  })
  .superRefine((value, context) => {
    if (value.assignment === 'UNIT' && !value.unitId) {
      context.addIssue({ code: 'custom', path: ['unitId'], message: 'Einheit auswählen' });
    }
    if (
      value.calibrationDataState === 'DATA_AVAILABLE' &&
      (!value.calibrationDate || !value.calibrationEvidenceRef.trim())
    ) {
      context.addIssue({
        code: 'custom',
        path: ['calibrationDate'],
        message: 'Eichdatum und Nachweis sind erforderlich',
      });
    }
    if (value.creationMode === 'REPLACEMENT') {
      if (
        !value.replacesMeterId ||
        !value.oldFinalValue ||
        !value.newInitialValue ||
        !value.replacementReason.trim()
      ) {
        context.addIssue({
          code: 'custom',
          path: ['replacesMeterId'],
          message: 'Vorgänger, beide Stände und Begründung sind erforderlich',
        });
      }
    }
    if (value.deviceType === 'GAS_METER') {
      const calorificFactor = Number(value.gasCalorificFactor.replace(',', '.'));
      const conditionNumber = Number(value.gasConditionNumber.replace(',', '.'));
      if (!Number.isFinite(calorificFactor) || calorificFactor <= 0) {
        context.addIssue({
          code: 'custom',
          path: ['gasCalorificFactor'],
          message: 'Positiven Brennwert eingeben',
        });
      }
      if (!Number.isFinite(conditionNumber) || conditionNumber <= 0) {
        context.addIssue({
          code: 'custom',
          path: ['gasConditionNumber'],
          message: 'Positive Zustandszahl eingeben',
        });
      }
      if (!value.gasValidFrom) {
        context.addIssue({
          code: 'custom',
          path: ['gasValidFrom'],
          message: 'Gültigkeitsbeginn eingeben',
        });
      }
      if (value.gasValidTo && value.gasValidTo <= value.gasValidFrom) {
        context.addIssue({
          code: 'custom',
          path: ['gasValidTo'],
          message: 'Das Enddatum muss nach dem Beginn liegen',
        });
      }
      if (!value.gasSupplierInvoiceReference.trim()) {
        context.addIssue({
          code: 'custom',
          path: ['gasSupplierInvoiceReference'],
          message: 'Belegreferenz eingeben',
        });
      }
    }
  });
type FormValues = z.infer<typeof FormSchema>;

function todayInput(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export function MeterWizard({ accountId }: { accountId: string }) {
  const search = useSearchParams();
  const workspace = useMeterWorkspace(accountId);
  const queryBuildingId = search.get('objektId') ?? '';
  const queryUnitId = search.get('einheitId') ?? '';
  const form = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      buildingId: queryBuildingId,
      assignment: queryUnitId ? 'UNIT' : 'BUILDING',
      unitId: queryUnitId,
      deviceType: 'HEAT_METER',
      serial: '',
      label: '',
      location: '',
      manufacturer: '',
      model: '',
      installedOn: todayInput(),
      remoteReadability: 'UNKNOWN',
      calibrationDataState: 'REVIEW_REQUIRED',
      calibrationDate: '',
      calibrationEvidenceRef: '',
      valuationFactor: '',
      creationMode: 'NEW',
      replacesMeterId: '',
      oldFinalValue: '',
      newInitialValue: '',
      replacementReason: '',
      gasCalorificFactor: '',
      gasConditionNumber: '',
      gasValidFrom: '',
      gasValidTo: '',
      gasSupplierInvoiceReference: '',
    },
  });
  const buildingId = form.watch('buildingId');
  const assignment = form.watch('assignment');
  const deviceType = form.watch('deviceType');
  const calibrationState = form.watch('calibrationDataState');
  const creationMode = form.watch('creationMode');
  const create = useCreateMeter(accountId, buildingId || 'new');
  const { draftRestored, clearDraft } = useFormDraft(
    `${accountId}.${buildingId || 'new'}.meter-create`,
    form,
  );

  useEffect(() => {
    if (deviceType === 'HEAT_COST_ALLOCATOR') {
      form.setValue('calibrationDataState', 'NOT_APPLICABLE');
      form.setValue('calibrationDate', '');
      form.setValue('calibrationEvidenceRef', '');
    } else if (form.getValues('calibrationDataState') === 'NOT_APPLICABLE') {
      form.setValue('calibrationDataState', 'REVIEW_REQUIRED');
    }
  }, [deviceType, form]);

  const selectedBuilding = workspace.data?.buildings.find((building) => building.id === buildingId);
  const units = selectedBuilding?.units ?? [];
  const selectedUnitId = assignment === 'UNIT' ? form.watch('unitId') : null;
  const activeMeters = [
    ...(selectedBuilding?.buildingMeters ?? []),
    ...units.flatMap((unit) => unit.meters),
  ].filter(
    (meter) =>
      meter.lifecycleStatus === 'ACTIVE' &&
      (assignment === 'BUILDING' ? meter.unitId === null : meter.unitId === selectedUnitId),
  );

  const submit = form.handleSubmit((values) => {
    const oldFinal = values.oldFinalValue ? parseMeterValueToX1000(values.oldFinalValue) : null;
    const newInitial = values.newInitialValue
      ? parseMeterValueToX1000(values.newInitialValue)
      : null;
    create.mutate(
      {
        unitId: values.assignment === 'UNIT' ? values.unitId : null,
        deviceType: values.deviceType,
        serial: values.serial.trim(),
        label: values.label.trim() || null,
        location: values.location.trim() || null,
        manufacturer: values.manufacturer.trim() || null,
        model: values.model.trim() || null,
        installedOn: values.installedOn,
        remoteReadability: values.remoteReadability,
        calibrationDataState: values.calibrationDataState,
        calibrationDate:
          values.calibrationDataState === 'DATA_AVAILABLE' ? values.calibrationDate : null,
        calibrationEvidenceRef:
          values.calibrationDataState === 'DATA_AVAILABLE'
            ? values.calibrationEvidenceRef.trim()
            : null,
        valuationFactorX1000:
          values.deviceType === 'HEAT_COST_ALLOCATOR' && values.valuationFactor
            ? Math.round(Number(values.valuationFactor.replace(',', '.')) * 1000)
            : null,
        creationMode: values.creationMode,
        replacesMeterId: values.creationMode === 'REPLACEMENT' ? values.replacesMeterId : null,
        replacementDate: values.creationMode === 'REPLACEMENT' ? values.installedOn : null,
        oldFinalValueX1000: values.creationMode === 'REPLACEMENT' ? oldFinal : null,
        newInitialValueX1000: values.creationMode === 'REPLACEMENT' ? newInitial : null,
        replacementReason:
          values.creationMode === 'REPLACEMENT' ? values.replacementReason.trim() : null,
        gasConversion:
          values.deviceType === 'GAS_METER'
            ? {
                calorificFactorKwhPerM3: values.gasCalorificFactor.replace(',', '.'),
                conditionNumber: values.gasConditionNumber.replace(',', '.'),
                validFrom: values.gasValidFrom,
                validTo: values.gasValidTo || null,
                supplierInvoiceReference: values.gasSupplierInvoiceReference.trim(),
              }
            : null,
      },
      { onSuccess: clearDraft },
    );
  });

  if (create.isSuccess) {
    return (
      <main className="py-10">
        <PageHeader title="Zähler angelegt" description="Gerät und Lifecycle wurden gespeichert." />
        <Card className="max-w-3xl">
          <CardContent className="space-y-5 pt-6">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Summary label="Gerätetyp" value={create.data.deviceTypeLabel} />
              <Summary label="Zählernummer" value={create.data.serial} />
              <Summary
                label="Zuordnung"
                value={create.data.unitLabel ?? 'Gebäude/Heizungsanlage'}
              />
              <Summary label="Maßeinheit" value={create.data.unitSymbol} />
            </dl>
            <div className="flex flex-wrap gap-2">
              <Button asChild>
                <Link href={`/a/${accountId}/zaehler?meterId=${create.data.id}`}>
                  Erste Ablesung erfassen
                </Link>
              </Button>
              <Button variant="outline" onClick={() => window.location.reload()}>
                Noch einen Zähler anlegen
              </Button>
              <Button asChild variant="ghost">
                <Link href={`/a/${accountId}/zaehler?meterId=${create.data.id}`}>
                  Fertig – zur Zählerliste
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (workspace.isPending) {
    return (
      <main className="py-10">
        <PageHeader title="Zähler anlegen" description="Gerätedaten werden vorbereitet." />
        <div
          aria-hidden="true"
          className="h-96 max-w-4xl animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      </main>
    );
  }

  if (workspace.isError) {
    return (
      <main className="py-10">
        <PageHeader title="Zähler anlegen" description="Gerät, Zuordnung und Eichdaten." />
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          <button className="underline" onClick={() => void workspace.refetch()}>
            Erneut versuchen
          </button>
        </StatusNote>
      </main>
    );
  }

  if (!workspace.data.permissions.canWrite) {
    return (
      <main className="py-10">
        <PageHeader title="Zähler anlegen" description="Diese Funktion ist nur für Eigentümer." />
        <StatusNote kind="warning" label="Nur lesender Zugriff.">
          Sie können den Zählerbestand ansehen, aber keine Geräte anlegen.
        </StatusNote>
      </main>
    );
  }

  if (workspace.data.buildings.length === 0) {
    return (
      <main className="py-10">
        <PageHeader title="Zähler anlegen" description="Zähler hängen an einem Objekt." />
        <StatusNote kind="warning" label="Noch kein Objekt vorhanden.">
          <Link
            className="font-semibold underline underline-offset-4"
            href={`/a/${accountId}/objekte/neu`}
          >
            Zuerst ein Objekt anlegen
          </Link>
        </StatusNote>
      </main>
    );
  }

  return (
    <main className="py-10">
      <PageHeader
        title="Zähler anlegen"
        description="Gerät, Zuordnung und Eichdaten in einem Schritt erfassen."
        breadcrumb={<Link href={`/a/${accountId}/zaehler`}>Zähler</Link>}
      />
      <form onSubmit={submit} noValidate className="max-w-4xl space-y-6">
        <WizardSection title="Zuordnung">
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Objekt"
              id="meter-building"
              registration={form.register('buildingId')}
            >
              <option value="">Bitte auswählen</option>
              {workspace.data?.buildings.map((building) => (
                <option key={building.id} value={building.id}>
                  {building.name}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Einbauort"
              id="meter-assignment"
              registration={form.register('assignment')}
            >
              <option value="BUILDING">Gebäude/Heizungsanlage</option>
              <option value="UNIT">Einheit</option>
            </SelectField>
            {assignment === 'UNIT' ? (
              <SelectField label="Einheit" id="meter-unit" registration={form.register('unitId')}>
                <option value="">Bitte auswählen</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.label}
                  </option>
                ))}
              </SelectField>
            ) : null}
            <FormField
              id="meter-location"
              label="Einbauort/Raum (optional)"
              hint="z. B. Wohnzimmer oder Heizzentrale"
              error={undefined}
              registration={form.register('location')}
            />
          </div>
        </WizardSection>

        <WizardSection title="Gerätetyp">
          <div className="grid gap-3 sm:grid-cols-2">
            {METER_DEVICE_TYPES.map((type) => (
              <label
                key={type}
                className={`cursor-pointer rounded-xl border p-4 ${deviceType === type ? 'border-green bg-mint/40' : 'border-mint bg-paper'}`}
              >
                <input
                  type="radio"
                  value={type}
                  className="mr-2"
                  {...form.register('deviceType')}
                />
                <span className="font-semibold">{METER_DEVICE_TYPE_LABELS[type]}</span>
                <span className="mt-1 block text-sm text-slate">
                  {MEASUREMENT_UNIT_LABELS[DEVICE_TYPE_UNIT[type]]}
                </span>
              </label>
            ))}
          </div>
        </WizardSection>

        <WizardSection title="Gerätedaten">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="meter-serial"
              label="Zählernummer"
              error={form.formState.errors.serial}
              registration={form.register('serial')}
            />
            <FormField
              id="meter-installed"
              label="Einbaudatum"
              type="date"
              error={form.formState.errors.installedOn}
              registration={form.register('installedOn')}
            />
            <FormField
              id="meter-manufacturer"
              label="Hersteller (optional)"
              error={undefined}
              registration={form.register('manufacturer')}
            />
            <FormField
              id="meter-model"
              label="Modell (optional)"
              error={undefined}
              registration={form.register('model')}
            />
            <FormField
              id="meter-label"
              label="Eigene Bezeichnung (optional)"
              error={undefined}
              registration={form.register('label')}
            />
            {deviceType === 'HEAT_COST_ALLOCATOR' ? (
              <FormField
                id="meter-factor"
                label="Bewertungsfaktor (optional)"
                hint="Bitte vom Gerät oder Messdienstleister übernehmen."
                inputMode="decimal"
                error={undefined}
                registration={form.register('valuationFactor')}
              />
            ) : null}
          </div>
        </WizardSection>

        {deviceType === 'GAS_METER' ? (
          <WizardSection title="Gasumrechnung">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="meter-gas-calorific-factor"
                label="Brennwert (kWh/m³)"
                inputMode="decimal"
                error={form.formState.errors.gasCalorificFactor}
                registration={form.register('gasCalorificFactor')}
              />
              <FormField
                id="meter-gas-condition-number"
                label="Zustandszahl"
                inputMode="decimal"
                error={form.formState.errors.gasConditionNumber}
                registration={form.register('gasConditionNumber')}
              />
              <FormField
                id="meter-gas-valid-from"
                label="Gültig ab"
                type="date"
                error={form.formState.errors.gasValidFrom}
                registration={form.register('gasValidFrom')}
              />
              <FormField
                id="meter-gas-valid-to"
                label="Gültig bis (optional)"
                type="date"
                error={form.formState.errors.gasValidTo}
                registration={form.register('gasValidTo')}
              />
              <FormField
                id="meter-gas-supplier-reference"
                label="Versorgerrechnung / Belegreferenz"
                error={form.formState.errors.gasSupplierInvoiceReference}
                registration={form.register('gasSupplierInvoiceReference')}
              />
            </div>
          </WizardSection>
        ) : null}

        <WizardSection title="Fernablesbarkeit">
          <SelectField
            label="Status"
            id="meter-remote"
            registration={form.register('remoteReadability')}
          >
            <option value="REMOTE_READABLE">Fernablesbar</option>
            <option value="NOT_REMOTE_READABLE">Nicht fernablesbar</option>
            <option value="UNKNOWN">Unbekannt</option>
          </SelectField>
          {form.watch('remoteReadability') === 'REMOTE_READABLE' ? (
            <p className="mt-3 text-sm text-slate">
              Fernablesbares Gerät. Die automatische Übertragung von Funkablesungen an Lokara ist
              für eine spätere Version vorgesehen. Ablesungen werden derzeit manuell erfasst.
            </p>
          ) : null}
        </WizardSection>

        <WizardSection title="Eichangaben">
          <SelectField
            label="Eichdatenzustand"
            id="meter-calibration-state"
            registration={form.register('calibrationDataState')}
          >
            <option value="DATA_AVAILABLE">Eichpflichtig – Eichdaten vorhanden</option>
            <option value="MISSING_DATA">Eichpflichtig – Eichdaten fehlen</option>
            <option value="NOT_APPLICABLE">Nicht eichpflichtig</option>
            <option value="REVIEW_REQUIRED">Unklar – später prüfen</option>
          </SelectField>
          {calibrationState === 'DATA_AVAILABLE' ? (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <FormField
                id="meter-calibration-date"
                label="Eichdatum"
                type="date"
                error={form.formState.errors.calibrationDate}
                registration={form.register('calibrationDate')}
              />
              <FormField
                id="meter-calibration-ref"
                label="Nachweis/Quelle"
                error={undefined}
                registration={form.register('calibrationEvidenceRef')}
              />
            </div>
          ) : null}
        </WizardSection>

        <WizardSection title="Anlegeart">
          <SelectField
            label="Vorgang"
            id="meter-creation-mode"
            registration={form.register('creationMode')}
          >
            <option value="NEW">Neuen Zähler einbauen</option>
            <option value="EXISTING">Bestehenden Zähler nachtragen</option>
            <option value="REPLACEMENT">Vorhandenen Zähler ersetzen</option>
          </SelectField>
          {creationMode === 'REPLACEMENT' ? (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <SelectField
                label="Vorgänger"
                id="meter-predecessor"
                registration={form.register('replacesMeterId')}
              >
                <option value="">Bitte auswählen</option>
                {activeMeters.map((meter) => (
                  <option key={meter.id} value={meter.id}>
                    {meter.deviceTypeLabel} · {meter.serial}
                  </option>
                ))}
              </SelectField>
              <FormField
                id="meter-replacement-reason"
                label="Wechselgrund"
                error={undefined}
                registration={form.register('replacementReason')}
              />
              <FormField
                id="meter-old-final"
                label="Schlussstand Vorgänger"
                inputMode="decimal"
                error={undefined}
                registration={form.register('oldFinalValue')}
              />
              <FormField
                id="meter-new-initial"
                label="Anfangsstand neues Gerät"
                inputMode="decimal"
                error={undefined}
                registration={form.register('newInitialValue')}
              />
            </div>
          ) : null}
        </WizardSection>

        {draftRestored ? (
          <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
            Ihre letzten Eingaben wurden automatisch gesichert.
          </StatusNote>
        ) : null}
        {create.isError ? (
          <StatusNote kind="danger" label="Anlegen fehlgeschlagen.">
            {create.error instanceof ApiError && create.error.detail
              ? create.error.detail
              : 'Bitte Eingaben prüfen und erneut versuchen.'}
          </StatusNote>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" disabled={create.isPending || !buildingId}>
            {create.isPending ? 'Wird angelegt…' : 'Zähler anlegen'}
          </Button>
          <Button asChild type="button" variant="ghost">
            <Link href={`/a/${accountId}/zaehler`}>
              Abbrechen
            </Link>
          </Button>
        </div>
      </form>
    </main>
  );
}

function WizardSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function SelectField({
  label,
  id,
  registration,
  children,
}: {
  label: string;
  id: string;
  registration: object;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select id={id} {...registration}>
        {children}
      </Select>
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-slate">{label}</dt>
      <dd className="font-semibold text-ink">{value}</dd>
    </div>
  );
}
