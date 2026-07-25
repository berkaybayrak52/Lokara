'use client';

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

import { API_URL, ApiError } from '@/lib/api';
import type { DemoStatementResponse } from '@/lib/contracts';

import { useDemoStatement } from './queries';

/**
 * Abrechnung erstellen (docs/04 M3 page 6, docs/06 Scenario 1+2): run the
 * NK + heating/CO₂ statement, show the computed shares + the cent-exact
 * reconciliation, download the PDF the API renders.
 */
export function StatementPage({ accountId }: { accountId: string }) {
  const [requested, setRequested] = useState(false);
  const statement = useDemoStatement(accountId, requested);
  const pdfUrl = `${API_URL}/a/${accountId}/statements/demo/pdf`;

  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Abrechnung erstellen</h1>
        <p className="mt-2 max-w-prose text-slate">
          Betriebs- und Heizkostenabrechnung 01.01.2025 – 31.12.2025. Die Anteile berechnen die
          geprüften Engines — jede Kostenart stimmt centgenau mit dem Gesamtbetrag überein.
        </p>
      </header>

      {!requested ? (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Abrechnung 2025 berechnen</CardTitle>
            <CardDescription>
              Müllabfuhr 1.200,00&nbsp;€ nach Wohnfläche, Heiz- und Warmwasserkosten
              10.300,00&nbsp;€ inkl. CO₂-Aufteilung nach CO2KostAufG.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => setRequested(true)}>Abrechnung berechnen</Button>
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
              : 'Bitte API und Datenbank prüfen, dann erneut versuchen.'}
          </StatusNote>
          <Button variant="outline" onClick={() => statement.refetch()}>
            Erneut versuchen
          </Button>
        </div>
      ) : (
        <StatementResult data={statement.data} pdfUrl={pdfUrl} accountId={accountId} />
      )}
    </main>
  );
}

function StatementResult({
  data,
  pdfUrl,
  accountId,
}: {
  data: DemoStatementResponse;
  pdfUrl: string;
  accountId: string;
}) {
  return (
    <div className="max-w-4xl space-y-8">
      <section aria-labelledby="nk-heading">
        <h2 id="nk-heading" className="mb-3 font-display text-xl font-bold">
          Betriebskosten
        </h2>
        {data.nkCosts.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>Keine Betriebskosten im Zeitraum</CardTitle>
              <CardDescription>
                Für 2025 sind noch keine Kostenarten erfasst. Erfassen Sie sie unter{' '}
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
        <Card>
          <CardContent className="pt-6">
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
                    <TableCell className="text-right tabular-nums">{line.heatingBaseEur}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {line.heatingConsumptionEur}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{line.wwBaseEur}</TableCell>
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
          </CardContent>
        </Card>

        {data.co2 ? (
          <p className="mt-3 max-w-prose rounded-lg bg-mint p-4 text-sm leading-6">
            <strong>CO₂-Kostenaufteilung</strong> (CO2KostAufG, {data.co2.rechtsstand}):
            Emissionsintensität {data.co2.intensityDisplay}&nbsp;kg&nbsp;CO₂/m²/Jahr →
            Vermieteranteil {data.co2.landlordSharePercent}&nbsp;% ({data.co2.landlordAmountEur},
            vor der Umlage abgezogen); Mieteranteil {data.co2.renterAmountEur}.
          </p>
        ) : null}
        <ReconciliationNote
          reconciles={data.heatingTotalCents === data.heatingInputTotalCents}
          totalEur={data.heatingTotalEur}
        />
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
