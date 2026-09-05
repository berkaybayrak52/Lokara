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
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageHeader } from '@/features/portal/page-header';
import { API_URL, ApiError } from '@/lib/api';
import type {
  AdvancePaymentPeriodOut,
  UnitDashboardHistorySegment,
  UnitDashboardResponse,
} from '@/lib/contracts';
import { UnitAmenitySchema } from '@/lib/contracts';
import { isoToGermanDate, parseEurToCents } from '@/lib/format';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { useCreateTenancy, useCreateUnitProfileVersion, useUnitDashboard } from './queries';

const TenancyFormSchema = z
  .object({
    renterName: z.string().trim().min(1, 'Pflichtfeld'),
    validFrom: z.string().min(1, 'Pflichtfeld'),
    validTo: z.string(),
    baseRent: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((value) => parseEurToCents(value) !== null, 'Betrag wie 950,00 angeben'),
    advance: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((value) => parseEurToCents(value) !== null, 'Betrag wie 220,00 angeben'),
    advanceDeclarationRef: z.string().trim().min(1, 'Pflichtfeld').max(500),
  })
  .refine((values) => values.validTo === '' || values.validTo >= values.validFrom, {
    path: ['validTo'],
    message: 'Der letzte Miettag darf nicht vor dem Beginn liegen',
  });
type TenancyForm = z.infer<typeof TenancyFormSchema>;

const EMPTY_TENANCY: TenancyForm = {
  renterName: '',
  validFrom: '',
  validTo: '',
  baseRent: '',
  advance: '',
  advanceDeclarationRef: 'Mietvertrag',
};

const ProfileFormSchema = z.object({
  effectiveFrom: z.string().min(1, 'Pflichtfeld'),
  usageType: z.enum(['RESIDENTIAL', 'COMMERCIAL', 'OTHER']),
  rooms: z
    .string()
    .refine(
      (value) => value === '' || /^\d+(?:[,.]\d{1,2})?$/.test(value),
      'Zimmerzahl wie 3 oder 2,5 angeben',
    ),
  amenities: z.array(UnitAmenitySchema),
  amenityNote: z.string().max(500, 'Maximal 500 Zeichen'),
  evidenceRef: z.string().trim().min(1, 'Pflichtfeld').max(500),
});
type ProfileForm = z.infer<typeof ProfileFormSchema>;

const AMENITIES = [
  ['BALCONY', 'Balkon'],
  ['TERRACE', 'Terrasse'],
  ['ELEVATOR', 'Aufzug'],
  ['CELLAR', 'Keller'],
  ['FITTED_KITCHEN', 'Einbauküche'],
  ['BARRIER_REDUCED', 'Barrierearm'],
] as const;

export function selectAdvancePaymentAmount(
  schedule: AdvancePaymentPeriodOut[],
  todayIso: string,
): string | null {
  if (schedule.length === 0) return null;
  const latestFirst = [...schedule].sort((left, right) =>
    right.validFrom.localeCompare(left.validFrom),
  );
  const current = latestFirst.find(
    (period) =>
      period.validFrom <= todayIso && (period.validTo === null || todayIso < period.validTo),
  );
  return (current ?? latestFirst[0])?.amountEur ?? null;
}

function nextDay(iso: string): string {
  const value = new Date(`${iso}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + 1);
  return value.toISOString().slice(0, 10);
}

function stateClass(state: UnitDashboardResponse['state']): string {
  if (state === 'RENTED') return 'bg-success-tint text-success';
  if (state === 'CONFLICT') return 'bg-danger-tint text-danger';
  if (state === 'VACANT') return 'bg-warning-tint text-warning';
  return 'bg-mint text-ink';
}

export function UnitDetailPage({ accountId, unitId }: { accountId: string; unitId: string }) {
  const searchParams = useSearchParams();
  const dashboard = useUnitDashboard(accountId, unitId);
  const [showProfile, setShowProfile] = useState(false);
  const [tenancyEntry, setTenancyEntry] = useState<'closed' | 'choice' | 'manual'>(
    searchParams.get('createTenancy') === '1' ? 'manual' : 'closed',
  );

  if (dashboard.isPending) {
    return (
      <main className="py-10" aria-busy="true" aria-label="Einheit wird geladen">
        <div
          aria-hidden="true"
          className="h-72 max-w-6xl animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      </main>
    );
  }
  if (dashboard.isError) {
    const missing = dashboard.error instanceof ApiError && dashboard.error.status === 404;
    return (
      <main className="py-10">
        <StatusNote
          kind="danger"
          label={missing ? 'Einheit nicht gefunden.' : 'Dashboard konnte nicht geladen werden.'}
        >
          {missing ? (
            <Link className="underline underline-offset-4" href={`/a/${accountId}/objekte`}>
              Zurück zur Objektliste
            </Link>
          ) : (
            <button
              type="button"
              className="underline underline-offset-4"
              onClick={() => void dashboard.refetch()}
            >
              Erneut versuchen
            </button>
          )}
        </StatusNote>
      </main>
    );
  }

  const unit = dashboard.data;
  const primaryAction = unit.primaryAction;
  return (
    <main className="py-10">
      <PageHeader
        title={unit.label}
        description={`${unit.buildingAddress} · Stand ${isoToGermanDate(unit.asOf)}`}
        status={
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${stateClass(unit.state)}`}
          >
            {unit.stateLabel}
          </span>
        }
        breadcrumb={
          <>
            <Link href={`/a/${accountId}/objekte`} className="text-green hover:underline">
              Objekte
            </Link>{' '}
            <span aria-hidden="true">/</span>{' '}
            <Link
              href={`/a/${accountId}/objekte/${unit.buildingId}`}
              className="text-green hover:underline"
            >
              {unit.buildingName}
            </Link>
          </>
        }
        actions={
          <>
            {unit.permissions.canEditProfile ? (
              <Button type="button" variant="outline" onClick={() => setShowProfile(true)}>
                {unit.profile.version ? 'Eckdaten aktualisieren' : 'Eckdaten ergänzen'}
              </Button>
            ) : null}
            {primaryAction?.key === 'CREATE_TENANCY' ? (
              <Button
                id="create-tenancy-action"
                type="button"
                onClick={() => setTenancyEntry('choice')}
              >
                {primaryAction.label}
              </Button>
            ) : primaryAction ? (
              <Button asChild>
                <a href={primaryAction.href}>{primaryAction.label}</a>
              </Button>
            ) : null}
          </>
        }
      />

      <div className="flex max-w-6xl flex-col gap-6">
        {unit.state === 'CONFLICT' ? (
          <StatusNote kind="danger" label="Zeitangaben überschneiden sich.">
            Für diesen Stichtag kann kein eindeutiger Einheitenstatus gezeigt werden.
          </StatusNote>
        ) : null}

        <FactsCard unit={unit} />
        {showProfile ? (
          <ProfileEditor accountId={accountId} unit={unit} onClose={() => setShowProfile(false)} />
        ) : null}

        {unit.currentTenancy ? (
          <CurrentTenancy unit={unit} />
        ) : (
          <Card id="aktuelles-mietverhaeltnis">
            <CardHeader>
              <CardTitle>Aktuelles Mietverhältnis</CardTitle>
              <CardDescription>
                Zum Stichtag ist kein laufendes Mietverhältnis dokumentiert.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {tenancyEntry === 'choice' && unit.permissions.canCreateTenancy ? (
          <Card>
            <CardHeader>
              <CardTitle>Mietverhältnis erstellen</CardTitle>
              <CardDescription>Wählen Sie, wie die Vertragsdaten übernommen werden.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Button asChild variant="outline" className="h-auto min-h-20 whitespace-normal py-4">
                <Link href={`/a/${accountId}/vertraege/neu?unitId=${unitId}`}>
                  <span>
                    <span className="block font-semibold">Mit Vertragsgenerator</span>
                    <span className="mt-1 block text-sm font-normal">
                      Vertrag erzeugen und Daten automatisch übernehmen
                    </span>
                  </span>
                </Link>
              </Button>
              <div className="flex min-h-20 flex-col justify-center rounded-lg border border-mint p-4">
                <Button type="button" variant="outline" onClick={() => setTenancyEntry('manual')}>
                  Vertragsdaten selbst einpflegen
                </Button>
                <p className="mt-2 text-sm text-slate">Bestehende Angaben manuell erfassen</p>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {tenancyEntry === 'manual' && unit.permissions.canCreateTenancy ? (
          <CreateTenancyForm
            accountId={accountId}
            unitId={unitId}
            onClose={() => {
              setTenancyEntry('closed');
              requestAnimationFrame(() =>
                document.getElementById('create-tenancy-action')?.focus(),
              );
            }}
          />
        ) : null}

        <details id="mietverlauf" className="group rounded-xl bg-card shadow-sm">
          <summary className="cursor-pointer list-none rounded-xl p-6 font-display text-xl font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            Miet- und Nutzungsverlauf
            <span className="ml-2 font-sans text-sm font-normal text-slate">
              {unit.historyTotal} {unit.historyTotal === 1 ? 'Zeitraum' : 'Zeiträume'}
            </span>
          </summary>
          <div className="px-6 pb-6">
            <UnitHistory segments={unit.history} />
            {unit.historyHasMore ? (
              <p className="mt-3 text-sm text-slate">Gezeigt werden die zehn neuesten Zeiträume.</p>
            ) : null}
          </div>
        </details>

        <div className="grid gap-6 lg:grid-cols-2">
          <DocumentsCard unit={unit} />
          <ModulesCard accountId={accountId} unit={unit} />
        </div>
      </div>
    </main>
  );
}

function FactsCard({ unit }: { unit: UnitDashboardResponse }) {
  const tenancy = unit.currentTenancy;
  const positions = tenancy?.positions ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Eckdaten</CardTitle>
        <CardDescription>
          Dokumentierte Angaben der Einheit zum gemeinsamen Stichtag.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
          <Fact label="Fläche" value={`${unit.areaSqmDisplay} m²`} />
          <Fact
            label="Zimmer"
            value={unit.profile.roomsDisplay ? unit.profile.roomsDisplay : 'Nicht dokumentiert'}
          />
          <Fact label="Nutzung" value={unit.profile.usageLabel} />
          <Fact label="Kaltmiete" value={tenancy?.coldRentEur ?? 'Nicht belegt'} />
          <Fact
            label="Kaltmiete je m²"
            value={
              tenancy?.coldRentPerSqmEur ? `${tenancy.coldRentPerSqmEur} €/m²` : 'Nicht belegt'
            }
          />
          <Fact
            label="Garage / Stellplatz"
            value={
              positions.length > 0
                ? positions.map((position) => position.positionLabel).join(', ')
                : 'Nicht dokumentiert'
            }
          />
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate">
              Ausstattung
            </dt>
            <dd className="mt-1 text-sm font-medium text-ink">
              {unit.profile.amenityLabels.length > 0
                ? unit.profile.amenityLabels.join(' · ')
                : 'Nicht dokumentiert'}
              {unit.profile.amenityNote ? ` · ${unit.profile.amenityNote}` : ''}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate">{label}</dt>
      <dd className="mt-1 font-semibold tabular-nums text-ink">{value}</dd>
    </div>
  );
}

function CurrentTenancy({ unit }: { unit: UnitDashboardResponse }) {
  const tenancy = unit.currentTenancy;
  if (!tenancy) return null;
  return (
    <Card id="aktuelles-mietverhaeltnis">
      <CardHeader>
        <CardTitle>Aktuelles Mietverhältnis</CardTitle>
        <CardDescription>
          Seit {isoToGermanDate(tenancy.validFrom)}
          {tenancy.validTo
            ? ` · letzter Miettag ${isoToGermanDate(tenancy.validTo)}`
            : ' · unbefristet'}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <h4 className="text-sm font-semibold text-ink">Vertragsparteien</h4>
          <ul className="mt-2 space-y-2">
            {tenancy.parties.map((party) => (
              <li key={party.id} className="rounded-lg border border-mint px-3 py-2 text-sm">
                <span className="font-semibold">{party.name}</span>
                {party.email ? <span className="ml-2 text-slate">{party.email}</span> : null}
              </li>
            ))}
          </ul>
          {tenancy.parties.length === 0 ? (
            <p className="mt-2 text-sm text-slate">Keine Vertragspartei dokumentiert.</p>
          ) : null}
          <p className="mt-4 text-sm text-slate">
            {tenancy.contractTypeLabel}
            {tenancy.contractEvidenceRef ? ` · Nachweis: ${tenancy.contractEvidenceRef}` : ''}
          </p>
          {tenancy.positions.map((position) => (
            <p key={position.id} className="mt-2 text-sm text-slate">
              {position.positionLabel}
              {position.label ? ` ${position.label}` : ''} · {position.inclusionLabel}
              {position.monthlyAmountEur ? ` · ${position.monthlyAmountEur}` : ''}
            </p>
          ))}
        </div>
        <dl className="grid grid-cols-2 gap-4 rounded-xl bg-paper p-4">
          <Fact label="Kaltmiete" value={tenancy.coldRentEur} />
          <Fact label="NK-Vorauszahlung" value={tenancy.advancePaymentEur} />
          <div className="col-span-2 border-t border-mint pt-4">
            <Fact label="Monatlich gesamt" value={tenancy.totalMonthlyEur} />
          </div>
          {tenancy.lastRentChange ? (
            <div className="col-span-2 text-sm text-slate">
              Letzte dokumentierte Mietänderung: {tenancy.lastRentChange.newBaseRentEur} ab{' '}
              {isoToGermanDate(tenancy.lastRentChange.effectiveFrom)} ·{' '}
              {tenancy.lastRentChange.evidenceRef}
            </div>
          ) : null}
        </dl>
      </CardContent>
    </Card>
  );
}

function UnitHistory({ segments }: { segments: UnitDashboardHistorySegment[] }) {
  return (
    <ol className="space-y-3">
      {segments.map((segment) => (
        <li
          key={`${segment.kind}-${segment.validFrom}`}
          className="grid gap-1 border-l-4 border-mint pl-4 sm:grid-cols-[10rem_1fr]"
        >
          <span className="text-sm tabular-nums text-slate">
            {isoToGermanDate(segment.validFrom)} –{' '}
            {segment.validTo ? isoToGermanDate(segment.validTo) : 'heute'}
          </span>
          <span className="text-sm font-semibold text-ink">
            {segment.label}
            {segment.partyNames.length > 0 ? ` · ${segment.partyNames.join(', ')}` : ''}
            {segment.current ? ' · aktuell' : ''}
          </span>
        </li>
      ))}
    </ol>
  );
}

function DocumentsCard({ unit }: { unit: UnitDashboardResponse }) {
  const module = unit.modules.find((item) => item.key === 'DOCUMENTS');
  return (
    <Card>
      <CardHeader>
        <CardTitle>Dokumente</CardTitle>
        <CardDescription>
          Finalisierte Archivdokumente des aktuellen Mietverhältnisses.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {module && !module.available ? (
          <p className="text-sm text-slate">{module.unavailableReason}</p>
        ) : unit.documents.length === 0 ? (
          <p className="text-sm text-slate">Noch keine finalisierten Dokumente vorhanden.</p>
        ) : (
          <ul className="space-y-3">
            {unit.documents.map((document) => (
              <li key={document.id}>
                <a
                  href={`${API_URL}${document.downloadHref}`}
                  download
                  className="font-semibold text-green underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  {document.filename}
                </a>
                <p className="text-xs text-slate">
                  {(document.sizeBytes / 1024).toLocaleString('de-DE', {
                    maximumFractionDigits: 1,
                  })}{' '}
                  KB · archiviert {isoToGermanDate(document.createdAt.slice(0, 10))}
                </p>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-slate">
          Neue Dateien werden hier nicht hochgeladen. Diese Liste zeigt nur unveränderliche Archive.
        </p>
      </CardContent>
    </Card>
  );
}

function ModulesCard({ accountId, unit }: { accountId: string; unit: UnitDashboardResponse }) {
  const labels: Record<string, string> = {
    PAYMENTS: 'Zahlungen',
    PORTAL: 'Mieterportal',
    MESSAGES: 'Nachrichten',
  };
  return (
    <Card>
      <CardHeader>
        <CardTitle>Weitere Bereiche</CardTitle>
        <CardDescription>
          Nur bereits verfügbare Funktionen werden als Aktion angeboten.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {unit.modules
          .filter((module) => module.key !== 'DOCUMENTS')
          .map((module) => (
            <div key={module.key} className="border-b border-mint pb-3 last:border-0 last:pb-0">
              <p className="font-semibold text-ink">{labels[module.key]}</p>
              {module.key === 'PAYMENTS' && module.available ? (
                <Link
                  className="text-sm font-semibold text-forest underline underline-offset-4"
                  href={`/a/${accountId}/zahlungen`}
                >
                  Zahlungsarbeitsfläche öffnen
                </Link>
              ) : (
                <p className="text-sm text-slate">{module.unavailableReason}</p>
              )}
            </div>
          ))}
      </CardContent>
    </Card>
  );
}

function ProfileEditor({
  accountId,
  unit,
  onClose,
}: {
  accountId: string;
  unit: UnitDashboardResponse;
  onClose: () => void;
}) {
  const create = useCreateUnitProfileVersion(accountId, unit.id);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const form = useForm<ProfileForm>({
    resolver: zodResolver(ProfileFormSchema),
    defaultValues: {
      effectiveFrom: unit.asOf,
      usageType: unit.profile.usageType ?? 'RESIDENTIAL',
      rooms: unit.profile.roomsDisplay ?? '',
      amenities: unit.profile.amenities,
      amenityNote: unit.profile.amenityNote ?? '',
      evidenceRef: '',
    },
  });
  useEffect(() => headingRef.current?.focus(), []);

  const onSubmit = form.handleSubmit((values) => {
    const roomsX100 =
      values.rooms === '' ? null : Math.round(Number(values.rooms.replace(',', '.')) * 100);
    create.mutate({
      effectiveFrom: values.effectiveFrom,
      usageType: values.usageType,
      roomsX100,
      amenities: values.amenities,
      amenityNote: values.amenityNote.trim() || null,
      evidenceRef: values.evidenceRef,
    });
  });

  return (
    <Card>
      <CardHeader>
        <h3 ref={headingRef} tabIndex={-1} className="font-display text-xl font-semibold">
          Eckdaten dokumentieren
        </h3>
        <CardDescription>
          Speichern legt eine neue Version an. Frühere Angaben bleiben erhalten.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-5 md:grid-cols-2" noValidate>
          <FormField
            id="profile-effective"
            type="date"
            label="Gültig ab"
            error={form.formState.errors.effectiveFrom}
            registration={form.register('effectiveFrom')}
          />
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="profile-usage">Nutzung</Label>
            <Select id="profile-usage" {...form.register('usageType')}>
              <option value="RESIDENTIAL">Wohnen</option>
              <option value="COMMERCIAL">Gewerbe</option>
              <option value="OTHER">Sonstige Nutzung</option>
            </Select>
          </div>
          <FormField
            id="profile-rooms"
            label="Zimmer"
            hint="Optional, z. B. 3 oder 2,5"
            inputMode="decimal"
            error={form.formState.errors.rooms}
            registration={form.register('rooms')}
          />
          <FormField
            id="profile-evidence"
            label="Nachweis / Quelle"
            hint="z. B. Mietvertrag vom TT.MM.JJJJ"
            error={form.formState.errors.evidenceRef}
            registration={form.register('evidenceRef')}
          />
          <fieldset className="md:col-span-2">
            <legend className="mb-2 text-sm font-medium text-ink">Ausstattung</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {AMENITIES.map(([value, label]) => (
                <label key={value} className="flex items-center gap-2 text-sm text-ink">
                  <input type="checkbox" value={value} {...form.register('amenities')} />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="flex flex-col gap-1.5 md:col-span-2">
            <Label htmlFor="profile-note">Ergänzende Ausstattungsnotiz</Label>
            <textarea
              id="profile-note"
              rows={3}
              className="rounded-lg border border-slate bg-white px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              {...form.register('amenityNote')}
            />
          </div>
          <div className="flex flex-wrap gap-2 md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Wird gespeichert…' : 'Neue Version speichern'}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              Schließen
            </Button>
          </div>
          {create.isError ? (
            <StatusNote className="md:col-span-2" kind="danger" label="Speichern fehlgeschlagen.">
              Bitte Angaben und Gültigkeitsdatum prüfen.
            </StatusNote>
          ) : null}
          {create.isSuccess ? (
            <StatusNote className="md:col-span-2" kind="success" label="Version gespeichert." />
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}

function CreateTenancyForm({
  accountId,
  unitId,
  onClose,
}: {
  accountId: string;
  unitId: string;
  onClose: () => void;
}) {
  const create = useCreateTenancy(accountId, unitId);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const form = useForm<TenancyForm>({
    resolver: zodResolver(TenancyFormSchema),
    defaultValues: EMPTY_TENANCY,
  });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.${unitId}.tenancy-create`, form);
  useEffect(() => headingRef.current?.focus(), []);

  const onSubmit = form.handleSubmit((values) => {
    const baseRentCents = parseEurToCents(values.baseRent);
    const initialAdvancePaymentCents = parseEurToCents(values.advance);
    if (baseRentCents === null || initialAdvancePaymentCents === null) return;
    create.mutate(
      {
        renterName: values.renterName,
        validFrom: values.validFrom,
        validTo: values.validTo === '' ? null : nextDay(values.validTo),
        baseRentCents,
        initialAdvancePaymentCents,
        advanceDeclarationRef: values.advanceDeclarationRef,
      },
      {
        onSuccess: () => {
          clearDraft();
          form.reset(EMPTY_TENANCY);
        },
      },
    );
  });
  const overlap = create.isError && create.error instanceof ApiError && create.error.status === 422;

  return (
    <Card>
      <CardHeader>
        <h3 ref={headingRef} tabIndex={-1} className="font-display text-xl font-semibold">
          Mietverhältnis anlegen
        </h3>
        <CardDescription>
          Vertragsangaben werden als neue, unveränderliche Datensätze gespeichert.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} noValidate className="grid gap-4 md:grid-cols-2">
          <FormField
            id="tenancy-renter"
            label="Mieter:in (voller Name)"
            error={form.formState.errors.renterName}
            registration={form.register('renterName')}
          />
          <FormField
            id="tenancy-from"
            label="Mietbeginn"
            type="date"
            error={form.formState.errors.validFrom}
            registration={form.register('validFrom')}
          />
          <FormField
            id="tenancy-to"
            label="Letzter Miettag"
            hint="Optional bei unbefristetem Vertrag"
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
            id="tenancy-advance-declaration"
            label="Grundlage der NK-Vorauszahlung"
            hint="z. B. Mietvertrag vom TT.MM.JJJJ"
            error={form.formState.errors.advanceDeclarationRef}
            registration={form.register('advanceDeclarationRef')}
          />
          <div className="flex flex-wrap gap-2 md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Wird angelegt…' : 'Mietverhältnis anlegen'}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              Schließen
            </Button>
          </div>
          {draftRestored ? (
            <StatusNote className="md:col-span-2" kind="warning" label="Entwurf wiederhergestellt.">
              Ihre letzten Eingaben wurden automatisch gesichert.
            </StatusNote>
          ) : null}
          {create.isError ? (
            <StatusNote className="md:col-span-2" kind="danger" label="Anlegen fehlgeschlagen.">
              {overlap
                ? 'Der Zeitraum überschneidet sich mit einem bestehenden Mietverhältnis oder ist ungültig.'
                : 'Bitte Eingaben prüfen und erneut versuchen.'}
            </StatusNote>
          ) : null}
          {create.isSuccess ? (
            <StatusNote className="md:col-span-2" kind="success" label="Gespeichert.">
              Das Mietverhältnis wurde angelegt.
            </StatusNote>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}
