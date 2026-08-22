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
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';
import React, { useState } from 'react';

import { API_URL, ApiError } from '@/lib/api';
import type { DemoStatementResponse } from '@/lib/contracts';

import { useBuildings } from '../objekte/queries';

import { useStatement } from './queries';

/**
 * Abrechnung erstellen (docs/04 M3 page 6, docs/06 Scenario 1+2): run the
 * NK + heating/CO₂ statement, show the computed shares + the cent-exact
 * reconciliation, download the PDF the API renders.
 */
/** The seeded demo period, and the value the pickers open on. */
const DEFAULT_PERIOD_FROM = '2025-01-01';
const DEFAULT_PERIOD_TO = '2025-12-31';

export function StatementPage({ accountId }: { accountId: string }) {
  const [requested, setRequested] = useState(false);
  const buildings = useBuildings(accountId);
  const [buildingId, setBuildingId] = useState('');
  const [periodFrom, setPeriodFrom] = useState(DEFAULT_PERIOD_FROM);
  const [periodTo, setPeriodTo] = useState(DEFAULT_PERIOD_TO);

  // The first object is the opening selection, not a fallback the run uses: a
  // statement is always computed for the object the user can see selected.
  const options = buildings.data?.buildings ?? [];
  const selectedId = buildingId || options[0]?.id || '';

  const statement = useStatement(
    accountId,
    { buildingId: selectedId, periodFrom, periodTo },
    requested && selectedId !== '',
  );
  const pdfQuery = new URLSearchParams({
    building_id: selectedId,
    period_from: periodFrom,
    period_to: periodTo,
  });
  const pdfUrl = `${API_URL}/a/${accountId}/statements/pdf?${pdfQuery}`;

  // Changing the selection invalidates the run that is on screen — showing last
  // period's figures under this period's heading is the one thing this screen
  // must never do.
  const reselect = (apply: () => void) => {
    apply();
    setRequested(false);
  };

  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Abrechnung erstellen</h1>
        <p className="mt-2 max-w-prose text-slate">
          Betriebs- und Heizkostenabrechnung für ein Objekt und einen Abrechnungszeitraum. Die
          Anteile berechnen die geprüften Engines — jede Kostenart stimmt centgenau mit dem
          Gesamtbetrag überein.
        </p>
      </header>

      {!requested ? (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Abrechnung berechnen</CardTitle>
            <CardDescription>
              Objekt und Abrechnungszeitraum wählen. Der Zeitraum ist tagesgenau und darf
              höchstens 12 Monate umfassen; Anfang und Ende zählen mit.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="statement-building">Objekt</Label>
              <Select
                id="statement-building"
                value={selectedId}
                disabled={options.length === 0}
                onChange={(event) => reselect(() => setBuildingId(event.target.value))}
              >
                {options.map((building) => (
                  <option key={building.id} value={building.id}>
                    {building.name} — {building.street}, {building.postalCode} {building.city}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex gap-4">
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="statement-from">Zeitraum von</Label>
                <Input
                  id="statement-from"
                  type="date"
                  value={periodFrom}
                  onChange={(event) => reselect(() => setPeriodFrom(event.target.value))}
                />
              </div>
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="statement-to">Zeitraum bis</Label>
                <Input
                  id="statement-to"
                  type="date"
                  value={periodTo}
                  onChange={(event) => reselect(() => setPeriodTo(event.target.value))}
                />
              </div>
            </div>
            {options.length === 0 ? (
              <StatusNote kind="warning" label="Noch kein Objekt angelegt.">
                Zuerst unter „Objekte“ ein Gebäude anlegen oder das Demo-Szenario laden.
              </StatusNote>
            ) : null}
            <Button disabled={selectedId === ''} onClick={() => setRequested(true)}>
              Abrechnung berechnen
            </Button>
          </CardContent>
        </Card>
      ) : statement.isPending ? (
        <div aria-hidden="true" className="max-w-4xl space-y-4">
          <div className="h-48 animate-pulse rounded-xl bg-mint/60" />
          <div className="h-48 animate-pulse rounded-xl bg-mint/60" />
        </div>
      ) : statement.isError ? (
        <div className="max-w-xl space-y-4">
          <StatusNote kind="danger" label="Berechnung fehlgeschlagen.">
            {statement.error instanceof ApiError && statement.error.status === 404
              ? 'Keine Daten im Konto — bitte zuerst das Demo-Szenario auf der Übersicht laden.'
              : // A 422 is entered data the landlord can fix (zu langer Zeitraum,
                // überschneidende Mietverhältnisse), and the API already says which
                // in German — `detail`, not `message`, which is the technical
                // "API request failed: 422 …" string.
                statement.error instanceof ApiError && statement.error.detail
                ? statement.error.detail
                : 'Bitte API und Datenbank prüfen, dann erneut versuchen.'}
          </StatusNote>
          <Button variant="outline" onClick={() => setRequested(false)}>
            Auswahl ändern
          </Button>
        </div>
      ) : (
        <StatementResult data={statement.data} pdfUrl={pdfUrl} accountId={accountId} />
      )}
    </main>
  );
}

export function StatementResult({
  data,
  pdfUrl,
  accountId,
}: {
  data: DemoStatementResponse;
  pdfUrl: string;
  accountId: string;
}) {
  // A confirmed Messdienstleister statement is passed through, not recomputed
  // (docs/03 H7), so its table has party totals and no §§ 7/8/9 split. The
  // branch is decided here once, from the path the API reports.
  const isMdl = data.heatingPath === 'MDL_NET' || data.heatingPath === 'MDL_GROSS';

  return (
    <div className="max-w-4xl space-y-8">
      {/* The object and the period are selectable, so the result has to name
          which ones it computed — figures under the wrong heading is exactly
          what `reselect` above exists to prevent. */}
      <header>
        <h2 className="font-display text-2xl font-bold">{data.buildingName}</h2>
        <p className="mt-1 text-sm text-slate">
          {data.buildingAddress} · Abrechnungszeitraum {data.periodLabel}
        </p>
      </header>

      <section aria-labelledby="nk-heading">
        <h2 id="nk-heading" className="mb-3 font-display text-xl font-bold">
          Betriebskosten
        </h2>
        {data.nkCosts.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>Keine Betriebskosten im Zeitraum</CardTitle>
              <CardDescription>
                Für {data.periodLabel} sind noch keine Kostenarten erfasst. Erfassen Sie sie
                unter{' '}
                <Link
                  href={`/a/${accountId}/kosten`}
                  className="text-green underline underline-offset-4"
                >
                  Kosten erfassen
                </Link>{' '}
                — die Abrechnung rechnet danach automatisch neu.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : null}
        {data.nkCosts.map((cost) => (
          <Card key={cost.label}>
            <CardHeader>
              <CardTitle className="text-base">{cost.label}</CardTitle>
              <CardDescription>
                Umlageschlüssel: {cost.keyLabel} · Gesamt {cost.amountEur}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableCaption>
                  Verteilung {cost.label} ({cost.keyLabel}) auf die Parteien
                </TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Partei</TableHead>
                    <TableHead className="text-right">Bemessung</TableHead>
                    <TableHead className="text-right">Anteil</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cost.lines.map((line) => (
                    <TableRow key={line.partyLabel}>
                      <TableCell className={line.isLandlord ? 'text-slate' : undefined}>
                        {line.partyLabel}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {line.weightDisplay}
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">
                        {line.amountEur}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ))}
        <ReconciliationNote
          reconciles={data.nkTotalCents === data.nkInputTotalCents}
          totalEur={data.nkTotalEur}
        />
      </section>

      <section aria-labelledby="heating-heading">
        <h2 id="heating-heading" className="mb-3 font-display text-xl font-bold">
          Heiz- und Warmwasserkosten
        </h2>
        {data.heatingMissingReason ? (
          <>
            <StatusNote kind="warning" label="Keine Heizkostenabrechnung möglich.">
              {data.heatingMissingReason}
            </StatusNote>
            <p className="mt-3 max-w-prose text-sm text-slate">
              Die Betriebskosten oben sind davon unberührt.{' '}
              <Link
                href={`/a/${accountId}/zaehler`}
                className="text-green underline underline-offset-4"
              >
                Zähler und Heizkosten erfassen
              </Link>{' '}
              — danach rechnet die Abrechnung automatisch neu.
            </p>
          </>
        ) : (
          <>
            <Card>
              <CardContent className="pt-6">
                {isMdl ? (
                  // A confirmed Messdienstleister statement discloses one amount
                  // per party and no §§ 7/8/9 column split, so the columns are
                  // dropped rather than filled with placeholders — Lokara does
                  // not recompute a split the source document does not state.
                  <Table>
                    <TableCaption>
                      Bestätigte Abrechnung des Messdienstleisters — Beträge unverändert übernommen
                    </TableCaption>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Partei</TableHead>
                        <TableHead className="text-right">Summe</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.heatingLines.map((line) => (
                        <TableRow key={line.partyLabel}>
                          <TableCell className={line.isLandlord ? 'text-slate' : undefined}>
                            {line.partyLabel}
                          </TableCell>
                          <TableCell className="text-right font-semibold tabular-nums">
                            {line.totalEur}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <Table>
                    <TableCaption>
                      Aufteilung der Heiz- und Warmwasserkosten nach §§ 7–9 HeizkostenV
                    </TableCaption>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Partei</TableHead>
                        <TableHead className="text-right">Grundk. Heizung</TableHead>
                        <TableHead className="text-right">Verbrauch Heizung</TableHead>
                        <TableHead className="text-right">Grundk. Warmwasser</TableHead>
                        <TableHead className="text-right">Verbrauch Warmwasser</TableHead>
                        <TableHead className="text-right">Summe</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.heatingLines.map((line) => (
                        <TableRow key={line.partyLabel}>
                          <TableCell className={line.isLandlord ? 'text-slate' : undefined}>
                            {line.partyLabel}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {line.heatingBaseEur}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {line.heatingConsumptionEur}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {line.wwBaseEur}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {line.wwConsumptionEur}
                          </TableCell>
                          <TableCell className="text-right font-semibold tabular-nums">
                            {line.totalEur}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            {data.heatingSourceNote ? (
              <p className="mt-3 max-w-prose rounded-lg bg-mint p-4 text-sm leading-6">
                {data.heatingSourceNote}
              </p>
            ) : null}

            {data.co2 ? (
              <p className="mt-3 max-w-prose rounded-lg bg-mint p-4 text-sm leading-6">
                <strong>CO₂-Kostenaufteilung</strong> (CO2KostAufG, {data.co2.rechtsstand}):
                Emissionsintensität {data.co2.intensityDisplay}&nbsp;kg&nbsp;CO₂/m²/Jahr →
                Vermieteranteil {data.co2.landlordSharePercent}&nbsp;% ({data.co2.landlordAmountEur}
                , vor der Umlage abgezogen); Mieteranteil {data.co2.renterAmountEur}.
              </p>
            ) : null}
            <ReconciliationNote
              reconciles={data.heatingTotalCents === data.heatingInputTotalCents}
              totalEur={data.heatingTotalEur}
            />
          </>
        )}
        {data.heatingFindings.map((finding) => (
          <StatusNote
            key={finding.code}
            kind={finding.severity === 'BLOCKER' ? 'danger' : 'warning'}
            label={finding.severity === 'BLOCKER' ? 'Abrechnung blockiert.' : 'Prüfhinweis.'}
            className="mt-3"
          >
            {finding.message}
          </StatusNote>
        ))}

        {data.heatingDeviceEvidence.length > 0 ? (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Geräte- und Ableseprotokoll</CardTitle>
              <CardDescription>
                Bewertungsfaktor, Zeitraum und Zuordnung bleiben je Gerät nachvollziehbar.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableCaption>Ablesesegmente der Heizkostenverteiler</TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Gerät / Raum</TableHead>
                    <TableHead>Zuordnung</TableHead>
                    <TableHead className="text-right">Ablesung</TableHead>
                    <TableHead className="text-right">Faktor</TableHead>
                    <TableHead className="text-right">Einheiten</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.heatingDeviceEvidence.map((line) => (
                    <TableRow key={`${line.deviceId}-${line.opening}-${line.closing}`}>
                      <TableCell>
                        {line.deviceId} · {line.room}
                      </TableCell>
                      <TableCell>
                        {line.allocationKind === 'PARTY'
                          ? 'Mietverhältnis'
                          : line.allocationKind === 'OWNER'
                            ? 'Eigentümer'
                            : 'Jahreswert'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {line.estimated ? 'geschätzt' : `${line.opening} → ${line.closing}`}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {line.valuationFactor}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{line.units}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ) : null}

        {data.heatingProvenance.length > 0 ? (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Herkunft der Angaben</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {data.heatingProvenance.map((entry) => (
                  <li key={`${entry.code}-${entry.source}`}>
                    <strong>{entry.source}:</strong> {entry.detail}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}

        {data.heatingReductionRisks.map((risk) => (
          <StatusNote
            key={risk.code}
            kind="warning"
            label={`${risk.percent}-%-Risiko`}
            className="mt-3"
          >
            {risk.message} Einzelbeträge: {risk.amountsEur.join(' · ')}.
          </StatusNote>
        ))}

        {data.annualComparison ? (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Verbrauchsvergleich zum Vorjahr</CardTitle>
              <CardDescription>
                {data.annualComparison.state === 'READY'
                  ? 'Heizverbrauch mit bestätigten DWD-Klimafaktoren.'
                  : data.annualComparison.state === 'RAW_FALLBACK'
                    ? 'Heizverbrauch unbereinigt; DWD-Klimafaktor fehlt.'
                    : 'Ein Vorjahresvergleich ist noch nicht möglich.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.annualComparison.graphRequired && data.annualComparison.previousHeat ? (
                <div
                  role="img"
                  aria-label={`Heizverbrauch: Vorjahr ${data.annualComparison.previousHeat}, laufendes Jahr ${data.annualComparison.currentHeat}`}
                  className="space-y-3"
                >
                  <ComparisonBar
                    label="Vorjahr"
                    value={data.annualComparison.previousHeat}
                    current={data.annualComparison.currentHeat}
                    previous={data.annualComparison.previousHeat}
                  />
                  <ComparisonBar
                    label="Laufendes Jahr"
                    value={data.annualComparison.currentHeat}
                    current={data.annualComparison.currentHeat}
                    previous={data.annualComparison.previousHeat}
                  />
                </div>
              ) : null}
              {data.annualComparison.note ? (
                <p className="mt-3 text-sm text-slate">{data.annualComparison.note}</p>
              ) : null}
            </CardContent>
          </Card>
        ) : null}
      </section>

      <section aria-label="Dokument" className="flex flex-wrap items-center gap-4">
        <Button asChild>
          <a href={pdfUrl} download>
            PDF herunterladen
          </a>
        </Button>
        <p className="text-sm text-slate">
          {data.rechtsstaende.join(' · ')} — {data.disclaimer}
        </p>
      </section>
    </div>
  );
}

function comparisonBarWidth(value: string, current: string, previous: string): string {
  const parse = (input: string) => Number(input.replaceAll('.', '').replace(',', '.'));
  const maximum = Math.max(parse(current), parse(previous), 1);
  return `${Math.max(4, Math.round((parse(value) / maximum) * 100))}%`;
}

function ComparisonBar({
  label,
  value,
  current,
  previous,
}: {
  label: string;
  value: string;
  current: string;
  previous: string;
}) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className="tabular-nums">{value}</span>
      </div>
      <div className="h-3 rounded-full bg-mint">
        <div
          className="h-3 rounded-full bg-green"
          style={{ width: comparisonBarWidth(value, current, previous) }}
        />
      </div>
    </div>
  );
}

function ReconciliationNote({ reconciles, totalEur }: { reconciles: boolean; totalEur: string }) {
  // The engines assert reconciliation before anything leaves them; this is the
  // user-facing proof (and the danger branch would expose a contract break).
  return reconciles ? (
    <StatusNote kind="success" label="Centgenau abgestimmt." className="mt-3">
      Summe {totalEur} entspricht exakt den Gesamtkosten.
    </StatusNote>
  ) : (
    <StatusNote kind="danger" label="Abstimmung fehlgeschlagen." className="mt-3">
      Die Summe der Anteile weicht vom Gesamtbetrag ab — Abrechnung nicht verwenden.
    </StatusNote>
  );
}
