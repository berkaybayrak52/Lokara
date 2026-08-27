'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
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
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import {
  useCreateDeliveryAddress,
  useCreatePaymentInstruction,
  useDeliveryAddresses,
  useFinalizeStatement,
  usePaymentInstructions,
} from '@/features/portal/queries';
import { API_URL, ApiError } from '@/lib/api';
import type { StatementDraftReadiness } from '@/lib/contracts';

import { useStatementDraft, useStatementDraftReadiness, useUpdateStatementDraft } from './queries';

const STEPS = [
  'Grundlagen',
  'Absender & Konto',
  'Einheiten & Mietverhältnisse',
  'Kosten & Verteilung',
  'Prüfung & Vorauszahlungen',
  'Dokumente & Versand',
] as const;

const KEY_LABELS: Record<string, string> = {
  AREA: 'Wohnfläche',
  PERSONS: 'Personen',
  CONSUMPTION: 'Verbrauch',
  UNITS: 'Einheiten',
  DIRECT: 'Direktzuordnung',
  MEA: 'Miteigentumsanteile',
};

function eur(cents: number | null): string {
  if (cents === null) return 'Nicht bestätigt';
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
}

function statusLabel(status: string): string {
  return (
    {
      DRAFT: 'Entwurf',
      REVIEW_REQUIRED: 'Prüfung erforderlich',
      READY: 'Bereit',
      FINALIZED: 'Finalisiert',
      BLOCKER: 'Blockiert',
      WARNING: 'Hinweis',
    }[status] ?? status
  );
}

export function StatementWizardPage({
  accountId,
  draftId,
  initialStep,
}: {
  accountId: string;
  draftId: string;
  initialStep?: number;
}) {
  const draft = useStatementDraft(accountId, draftId);
  const readiness = useStatementDraftReadiness(accountId, draftId);

  if (draft.isPending || readiness.isPending) {
    return (
      <main className="space-y-5 py-10">
        <div className="h-20 animate-pulse rounded-xl bg-mint/50 motion-reduce:animate-none" />
        <div className="h-[34rem] animate-pulse rounded-2xl bg-mint/50 motion-reduce:animate-none" />
      </main>
    );
  }
  if (draft.isError || readiness.isError || !readiness.data) {
    const error = draft.error ?? readiness.error;
    return (
      <main className="py-10">
        <StatusNote kind="danger" label="Abrechnungsentwurf konnte nicht geladen werden.">
          {error instanceof ApiError && error.detail
            ? error.detail
            : 'Laden Sie die Seite neu oder öffnen Sie den Entwurf aus der Abrechnungsliste.'}
        </StatusNote>
      </main>
    );
  }
  return (
    <StatementWizard
      key={readiness.data.draft.id}
      accountId={accountId}
      initial={readiness.data}
      initialStep={initialStep}
      onRefresh={() => readiness.refetch()}
    />
  );
}

function StatementWizard({
  accountId,
  initial,
  initialStep,
  onRefresh,
}: {
  accountId: string;
  initial: StatementDraftReadiness;
  initialStep?: number;
  onRefresh: () => Promise<unknown>;
}) {
  const router = useRouter();
  const draftId = initial.draft.id;
  const [step, setStep] = useState(
    Math.min(6, Math.max(1, initialStep ?? initial.draft.currentStep)),
  );
  const [title, setTitle] = useState(initial.draft.title);
  const [savedTitle, setSavedTitle] = useState(initial.draft.title);
  const [version, setVersion] = useState(initial.draft.version);
  const [selectedUnitIds] = useState(initial.draft.selectedUnitIds);
  const update = useUpdateStatementDraft(accountId, draftId);

  useEffect(() => {
    setVersion(initial.draft.version);
  }, [initial.draft.version]);

  useEffect(() => {
    if (title === savedTitle || update.isPending) return;
    const timer = window.setTimeout(() => {
      update
        .mutateAsync({ version, title, selectedUnitIds })
        .then((saved) => {
          setVersion(saved.version);
          setSavedTitle(saved.title);
        })
        .catch(() => undefined);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [savedTitle, selectedUnitIds, title, update, version]);

  const goTo = async (nextStep: number) => {
    try {
      const saved = await update.mutateAsync({
        version,
        title,
        selectedUnitIds,
        currentStep: nextStep,
      });
      setVersion(saved.version);
      setSavedTitle(saved.title);
      setStep(nextStep);
      await onRefresh();
      document.querySelector<HTMLElement>('#statement-step-heading')?.focus();
    } catch {
      // The persistent error below owns the message and recovery action.
    }
  };

  return (
    <main className="pb-32 pt-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            className="text-sm font-semibold text-green underline-offset-4 hover:underline"
            href={`/a/${accountId}/abrechnung`}
          >
            Zur Abrechnungsliste
          </Link>
          <h1 className="mt-3 font-display text-3xl font-bold">{title}</h1>
          <p className="mt-1 text-sm text-slate">
            {initial.draft.buildingName} · {initial.draft.periodStart} bis {initial.draft.periodEnd}
          </p>
        </div>
        <div className="text-right">
          <span className="inline-flex rounded-full bg-mint px-3 py-1 text-sm font-semibold text-forest">
            {statusLabel(initial.overallStatus)}
          </span>
          <p className="mt-2 text-xs text-slate" aria-live="polite">
            {update.isPending
              ? 'Wird gespeichert…'
              : update.isError
                ? 'Speichern fehlgeschlagen'
                : 'Gespeichert'}
          </p>
        </div>
      </div>

      <nav aria-label="Fortschritt der Abrechnung" className="sticky top-0 z-20 mb-8 bg-paper py-3">
        <ol className="grid grid-cols-6 gap-2">
          {STEPS.map((label, index) => {
            const number = index + 1;
            const active = number === step;
            const completed = number < step;
            return (
              <li key={label}>
                <button
                  type="button"
                  aria-current={active ? 'step' : undefined}
                  className={`w-full rounded-lg border px-2 py-2 text-left text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${
                    active
                      ? 'border-green bg-green text-white'
                      : completed
                        ? 'border-mint bg-mint text-forest'
                        : 'border-slate/40 bg-paper text-slate'
                  }`}
                  onClick={() => goTo(number)}
                >
                  <span className="block text-[11px]">
                    {completed ? 'Erledigt' : `Schritt ${number}`}
                  </span>
                  <span className="mt-0.5 block leading-tight">{label}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {update.isError ? (
        <div className="mb-5">
          <StatusNote kind="danger" label="Entwurf konnte nicht gespeichert werden.">
            {update.error instanceof ApiError && update.error.status === 409
              ? 'Der Entwurf wurde an anderer Stelle geändert.'
              : 'Bitte versuchen Sie es erneut.'}{' '}
            <button className="font-semibold underline" onClick={() => window.location.reload()}>
              Aktuelle Fassung laden
            </button>
          </StatusNote>
        </div>
      ) : null}

      <section aria-labelledby="statement-step-heading">
        <h2
          id="statement-step-heading"
          className="mb-5 font-display text-2xl font-bold outline-none"
          tabIndex={-1}
        >
          {STEPS[step - 1]}
        </h2>
        {step === 1 ? <BasicsStep initial={initial} title={title} setTitle={setTitle} /> : null}
        {step === 2 ? (
          <AddressAccountStep accountId={accountId} initial={initial} onChanged={onRefresh} />
        ) : null}
        {step === 3 ? <UnitsStep initial={initial} accountId={accountId} /> : null}
        {step === 4 ? <CostsStep initial={initial} accountId={accountId} /> : null}
        {step === 5 ? <ReviewStep initial={initial} accountId={accountId} /> : null}
        {step === 6 ? (
          <DocumentsStep accountId={accountId} initial={initial} onRefresh={onRefresh} />
        ) : null}
      </section>

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-mint bg-paper/95 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3">
          <Button
            variant="outline"
            disabled={step === 1 || update.isPending}
            onClick={() => goTo(step - 1)}
          >
            Zurück
          </Button>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              onClick={async () => {
                await goTo(step);
                router.push(`/a/${accountId}/abrechnung`);
              }}
            >
              Entwurf speichern und schließen
            </Button>
            {step < 6 ? (
              <Button disabled={update.isPending} onClick={() => goTo(step + 1)}>
                Weiter
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}

function BasicsStep({
  initial,
  title,
  setTitle,
}: {
  initial: StatementDraftReadiness;
  title: string;
  setTitle: (value: string) => void;
}) {
  const unitRows = useMemo(
    () => Array.from(new Map(initial.units.map((row) => [row.unitId, row])).values()),
    [initial.units],
  );
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Abrechnungsrahmen</CardTitle>
          <CardDescription>
            Objekt und Zeitraum bleiben für diesen Entwurf fest verbunden.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-1.5 lg:col-span-2">
            <Label htmlFor="statement-title">Titel</Label>
            <Input
              id="statement-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>
          <ReadOnlyValue label="Objekt" value={initial.draft.buildingName} />
          <ReadOnlyValue
            label="Abrechnungszeitraum"
            value={`${initial.draft.periodStart} bis ${initial.draft.periodEnd}`}
          />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Abrechnungsumfang</CardTitle>
          <CardDescription>
            Alle abrechnungsrelevanten Einheiten werden berücksichtigt. Leerstand, Eigennutzung und
            mietfreie Nutzung bleiben als eigene Zeitabschnitte nachvollziehbar.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Einheit</TableHead>
                  <TableHead>Nutzung im Zeitraum</TableHead>
                  <TableHead>Parteien</TableHead>
                  <TableHead>Einbezogen</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {unitRows.map((row) => (
                  <TableRow key={row.unitId}>
                    <TableCell className="font-medium">{row.label}</TableCell>
                    <TableCell>{row.usage}</TableCell>
                    <TableCell>{row.party}</TableCell>
                    <TableCell>Ja</TableCell>
                    <TableCell>{statusLabel(row.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AddressAccountStep({
  accountId,
  initial,
  onChanged,
}: {
  accountId: string;
  initial: StatementDraftReadiness;
  onChanged: () => Promise<unknown>;
}) {
  const tenantRows = initial.units.filter((row) => row.tenancyId !== null);
  const [tenancyId, setTenancyId] = useState(tenantRows[0]?.tenancyId ?? '');
  const [address, setAddress] = useState({
    addressee: '',
    street: '',
    postalCode: '',
    city: '',
    country: 'Deutschland',
  });
  const addresses = useDeliveryAddresses(accountId, initial.draft.buildingId, tenancyId ?? '');
  const createAddress = useCreateDeliveryAddress(
    accountId,
    initial.draft.buildingId,
    tenancyId ?? '',
  );
  const instructions = usePaymentInstructions(accountId);
  const createInstruction = useCreatePaymentInstruction(accountId);
  const [paymentText, setPaymentText] = useState(
    'Bitte überweisen Sie eine Nachzahlung unter Angabe der Einheit.',
  );
  const [creditText, setCreditText] = useState(
    'Ein Guthaben wird auf die bekannte Bankverbindung ausgezahlt.',
  );

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Absender</CardTitle>
          <CardDescription>
            Die gültige Vermieter- und Objektfassung wird bei der Finalisierung unverändert
            eingefroren.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ReadOnlyValue label="Objekt" value={initial.draft.buildingName} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Bankverbindung & Hinweise</CardTitle>
          <CardDescription>
            Änderungen erzeugen eine neue Version; alte Fassungen bleiben erhalten.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label htmlFor="payment-copy">Zahlungshinweis</Label>
          <Input
            id="payment-copy"
            value={paymentText}
            onChange={(event) => setPaymentText(event.target.value)}
          />
          <Label htmlFor="credit-copy">Guthabenhinweis</Label>
          <Input
            id="credit-copy"
            value={creditText}
            onChange={(event) => setCreditText(event.target.value)}
          />
          <Button
            variant="outline"
            disabled={!paymentText || !creditText || createInstruction.isPending}
            onClick={() =>
              createInstruction.mutate(
                { paymentText, creditText, validFrom: initial.draft.periodStart },
                { onSuccess: () => void onChanged() },
              )
            }
          >
            Als neue Version speichern
          </Button>
          <p className="text-sm text-slate">
            {instructions.data?.[0]
              ? `Aktuelle Fassung: v${instructions.data[0].version}`
              : 'Noch keine Fassung gespeichert'}
          </p>
        </CardContent>
      </Card>
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Zustelladressen</CardTitle>
          <CardDescription>
            Wählen Sie ein Mietverhältnis und ergänzen Sie nur fehlende Angaben.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select
            aria-label="Mietverhältnis"
            value={tenancyId ?? ''}
            onChange={(event) => setTenancyId(event.target.value)}
          >
            {tenantRows.map((row) => (
              <option key={row.tenancyId} value={row.tenancyId ?? ''}>
                {row.label} - {row.party}
              </option>
            ))}
          </Select>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Input
              aria-label="Empfänger"
              placeholder="Empfänger"
              value={address.addressee}
              onChange={(event) => setAddress({ ...address, addressee: event.target.value })}
            />
            <Input
              aria-label="Straße"
              placeholder="Straße und Hausnummer"
              value={address.street}
              onChange={(event) => setAddress({ ...address, street: event.target.value })}
            />
            <Input
              aria-label="Postleitzahl"
              placeholder="PLZ"
              value={address.postalCode}
              onChange={(event) => setAddress({ ...address, postalCode: event.target.value })}
            />
            <Input
              aria-label="Ort"
              placeholder="Ort"
              value={address.city}
              onChange={(event) => setAddress({ ...address, city: event.target.value })}
            />
            <Input
              aria-label="Land"
              placeholder="Land"
              value={address.country}
              onChange={(event) => setAddress({ ...address, country: event.target.value })}
            />
          </div>
          <Button
            variant="outline"
            disabled={
              !tenancyId ||
              !address.addressee ||
              !address.street ||
              !address.postalCode ||
              !address.city ||
              createAddress.isPending
            }
            onClick={() =>
              createAddress.mutate(
                { ...address, validFrom: initial.draft.periodStart },
                {
                  onSuccess: () => {
                    setAddress({
                      addressee: '',
                      street: '',
                      postalCode: '',
                      city: '',
                      country: 'Deutschland',
                    });
                    void onChanged();
                  },
                },
              )
            }
          >
            Adresse als neue Version speichern
          </Button>
          {(addresses.data ?? []).slice(0, 2).map((entry) => (
            <p key={entry.id} className="text-sm text-slate">
              v{entry.version}: {entry.addressee}, {entry.street}, {entry.postalCode} {entry.city}
            </p>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function UnitsStep({
  initial,
  accountId,
}: {
  initial: StatementDraftReadiness;
  accountId: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Alle Nutzungsabschnitte</CardTitle>
        <CardDescription>
          Mieterwechsel und Leerstand erscheinen als getrennte Zeilen.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Einheit</TableHead>
                <TableHead>Nutzung</TableHead>
                <TableHead>Name/Partei</TableHead>
                <TableHead>Nutzungszeitraum</TableHead>
                <TableHead>Ø Personen</TableHead>
                <TableHead>Fläche</TableHead>
                <TableHead>Vorauszahlungssoll</TableHead>
                <TableHead>Ist-Vorauszahlungen</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Aktion</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {initial.units.map((row) => (
                <TableRow key={`${row.unitId}-${row.tenancyId ?? row.usage}`}>
                  <TableCell className="font-medium">{row.label}</TableCell>
                  <TableCell>{row.usage}</TableCell>
                  <TableCell>{row.party}</TableCell>
                  <TableCell className="whitespace-nowrap">{row.periodLabel}</TableCell>
                  <TableCell>{row.personCount}</TableCell>
                  <TableCell>{row.areaSqm.replace('.', ',')} m²</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {eur(row.contractualAdvanceCents)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {eur(row.actualAdvancesCents)}
                  </TableCell>
                  <TableCell>{statusLabel(row.status)}</TableCell>
                  <TableCell>
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/a/${accountId}/einheiten/${row.unitId}`}>Prüfen</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function CostsStep({
  initial,
  accountId,
}: {
  initial: StatementDraftReadiness;
  accountId: string;
}) {
  const total = initial.costs.reduce((sum, row) => sum + row.amountCents, 0);
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Betriebskosten</CardTitle>
          <CardDescription>
            Wirksame, nicht stornierte Kosten werden genau einmal übernommen.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Kostenart</TableHead>
                  <TableHead>Zeitraum</TableHead>
                  <TableHead>Gesamtkosten</TableHead>
                  <TableHead>Umlagefähig</TableHead>
                  <TableHead>Verteilerschlüssel</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {initial.costs.map((row) => (
                  <TableRow key={row.costId}>
                    <TableCell className="font-medium">{row.label}</TableCell>
                    <TableCell>{row.periodLabel}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {eur(row.amountCents)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {eur(row.allocableCents)}
                    </TableCell>
                    <TableCell>{KEY_LABELS[row.allocationKey] ?? row.allocationKey}</TableCell>
                    <TableCell>{statusLabel(row.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex flex-wrap justify-between gap-3 border-t border-mint pt-4 font-semibold">
            <span>Gesamtkosten</span>
            <span className="tabular-nums">{eur(total)}</span>
          </div>
          <Button asChild variant="outline">
            <Link href={`/a/${accountId}/kosten/neu`}>Kosten hinzufügen</Link>
          </Button>
          <p className="text-sm text-slate">
            Kosten lassen sich schneller und sicherer vorbereiten, wenn Sie sie vorab unter „Kosten“
            erfassen. Der zukünftige E-Mail-Belegimport ist noch nicht aktiv.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Heiz- und Warmwasserkosten</CardTitle>
        </CardHeader>
        <CardContent>
          <StatusNote
            kind={initial.heatingPath ? 'success' : 'warning'}
            label={
              initial.heatingPath === 'SELF_BILLING'
                ? 'Mit Lokara berechnen'
                : initial.heatingPath
                  ? 'Messdienstleister-Abrechnung übernehmen'
                  : 'Heizkostenpfad noch nicht bereit'
            }
          >
            {initial.heatingPath
              ? 'Der Backend-Pfad ist eindeutig gewählt. Eigen- und Fremdergebnis werden nicht addiert.'
              : 'Prüfen Sie Kosten, Zähler und Ablesungen.'}
          </StatusNote>
        </CardContent>
      </Card>
    </div>
  );
}

function ReviewStep({
  initial,
  accountId,
}: {
  initial: StatementDraftReadiness;
  accountId: string;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Betriebskosten" value={eur(initial.nkTotalCents)} />
        <SummaryCard label="Heizkosten" value={eur(initial.heatingTotalCents)} />
        <SummaryCard label="Umlagefähige Summe" value={eur(initial.allocableTotalCents)} />
        <SummaryCard label="Eigentümeranteil" value={eur(initial.ownerTotalCents)} />
      </div>
      {initial.findings.length ? (
        <Findings findings={initial.findings} accountId={accountId} />
      ) : (
        <StatusNote kind="success" label="Alle Prüfungen abgeschlossen.">
          Der Entwurf ist bereit zur Dokumentvorschau und Finalisierung.
        </StatusNote>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Salden je Mietverhältnis</CardTitle>
          <CardDescription>Nur bestätigte Ist-Vorauszahlungen bestimmen den Saldo.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Einheit</TableHead>
                  <TableHead>Partei</TableHead>
                  <TableHead>Bestätigte Ist-Vorauszahlungen</TableHead>
                  <TableHead>Saldo</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {initial.units
                  .filter((row) => row.tenancyId)
                  .map((row) => (
                    <TableRow key={row.tenancyId}>
                      <TableCell>{row.label}</TableCell>
                      <TableCell>{row.party}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {eur(row.actualAdvancesCents)}
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">
                        {row.saldoCents === null
                          ? 'Noch kein Ergebnis'
                          : `${row.saldoCents > 0 ? 'Nachzahlung' : row.saldoCents < 0 ? 'Guthaben' : 'Ausgeglichen'} ${eur(Math.abs(row.saldoCents))}`}
                      </TableCell>
                      <TableCell>{statusLabel(row.status)}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function DocumentsStep({
  accountId,
  initial,
  onRefresh,
}: {
  accountId: string;
  initial: StatementDraftReadiness;
  onRefresh: () => Promise<unknown>;
}) {
  const router = useRouter();
  const finalize = useFinalizeStatement(accountId, initial.draft.buildingId);
  const query = new URLSearchParams({
    building_id: initial.draft.buildingId,
    period_from: initial.draft.periodStart,
    period_to: initial.draft.periodEnd,
  });
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Dokumentvorschau</CardTitle>
          <CardDescription>
            Vorschauen tragen Entwurfsstatus und werden bei Änderungen neu erzeugt.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {initial.documents.map((document) => {
            const preview = document.tenancyId
              ? `${API_URL}/a/${accountId}/buildings/${initial.draft.buildingId}/statements/preview.pdf?draft_id=${initial.draft.id}&tenancy_id=${document.tenancyId}&document_type=${document.key.startsWith('cover-') ? 'COVER_LETTER' : 'TENANT_STATEMENT'}`
              : `${API_URL}/a/${accountId}/statements/pdf?${query}`;
            return (
              <div
                key={document.key}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-mint p-4"
              >
                <div>
                  <p className="font-semibold">{document.documentType}</p>
                  <p className="text-sm text-slate">
                    {document.recipient} · {document.readiness === 'READY' ? 'Bereit' : 'Blockiert'}
                  </p>
                </div>
                <Button asChild size="sm" variant="outline">
                  <a href={preview} target="_blank" rel="noreferrer">
                    Vorschau
                  </a>
                </Button>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <StatusNote kind="warning" label="Finalisierung und Zustellung sind getrennt.">
        Heute werden die finalen PDFs unveränderlich archiviert und heruntergeladen. Mieterportal
        und E-Mail bleiben inaktiv, bis ihre echten Zustellpfade freigegeben sind.
      </StatusNote>
      {initial.findings.length ? (
        <Findings findings={initial.findings} accountId={accountId} />
      ) : null}
      {finalize.isError ? (
        <StatusNote kind="danger" label="Finalisierung nicht möglich.">
          {finalize.error instanceof ApiError && finalize.error.detail
            ? finalize.error.detail
            : 'Bitte laden Sie die Prüfung neu.'}
        </StatusNote>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <Button
          disabled={initial.overallStatus !== 'READY' || finalize.isPending}
          onClick={() =>
            finalize.mutate(
              {
                draftId: initial.draft.id,
                draftVersion: initial.draft.version,
                periodStart: initial.draft.periodStart,
                periodEnd: initial.draft.periodEnd,
                supersedesStatementId: initial.draft.correctionOfStatementId ?? undefined,
              },
              {
                onSuccess: (statement) =>
                  router.push(`/a/${accountId}/abrechnung/archiv/${statement.id}`),
              },
            )
          }
        >
          Abrechnung finalisieren
        </Button>
        <Button disabled variant="outline">
          Mieterportal · Bald verfügbar
        </Button>
        <Button disabled variant="outline">
          E-Mail · Bald verfügbar
        </Button>
        <Button variant="outline" onClick={() => void onRefresh()}>
          Prüfung aktualisieren
        </Button>
      </div>
    </div>
  );
}

function Findings({
  findings,
  accountId,
}: {
  findings: StatementDraftReadiness['findings'];
  accountId: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Prüfpunkte</CardTitle>
        <CardDescription>Blocker und Hinweise kommen vollständig aus dem Backend.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {findings.map((finding) => (
            <li
              key={`${finding.code}-${finding.entityId ?? ''}`}
              className="rounded-xl border border-mint p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    {finding.area} · {statusLabel(finding.severity)}
                  </p>
                  <p className="mt-1 text-sm text-slate">{finding.message}</p>
                  {finding.provenance ? (
                    <p className="mt-1 text-xs text-slate">Quelle: {finding.provenance}</p>
                  ) : null}
                </div>
                {finding.correctionRoute ? (
                  <Button asChild size="sm" variant="outline">
                    <Link
                      href={
                        finding.correctionRoute.startsWith('/a/')
                          ? finding.correctionRoute
                          : `/a/${accountId}`
                      }
                    >
                      {finding.allowedActions[0] ?? 'Prüfen'}
                    </Link>
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="py-5">
        <p className="text-sm text-slate">{label}</p>
        <p className="mt-2 font-display text-2xl font-bold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
function ReadOnlyValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm font-semibold text-slate">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
