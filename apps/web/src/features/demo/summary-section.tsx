'use client';

import {
  Card,
  CardContent,
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';

import { useDemoSummary, useHealth } from './queries';

/**
 * Live data over the FastAPI backend: first request 401s (no session cookie),
 * the api.ts interceptor mints the session and replays — no explicit login
 * step in the dev flow.
 */
export function SummarySection() {
  const health = useHealth();
  const summary = useDemoSummary();

  return (
    <section aria-labelledby="api-heading">
      <h2 id="api-heading" className="mb-4 font-display text-2xl font-semibold">
        Live-Daten über die API
      </h2>

      {summary.isPending ? (
        <p className="rounded-lg bg-mint p-4 text-slate" role="status">
          Lädt Demo-Daten …
        </p>
      ) : summary.isError ? (
        <p role="alert" className="rounded-lg border border-slate bg-white p-4 text-ink">
          API nicht erreichbar. Bitte <code>docker compose up -d</code>,{' '}
          <code>uv run lokara-seed-demo</code> und <code>uv run lokara-api</code> ausführen.
        </p>
      ) : (
        <>
          <p className="mb-4 text-sm text-slate">
            Status: {health.data?.status === 'ok' ? 'API erreichbar' : 'unbekannt'} · Konto:{' '}
            {summary.data.accountName} · Gebäude: {summary.data.buildingAddress} (
            {summary.data.unitCount} Einheiten) — geladen über den Auth-Interceptor
            (HttpOnly-Cookie).
          </p>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableCaption>Mietverhältnisse im Demo-Gebäude</TableCaption>
                <TableHeader>
                  <TableRow className="border-t-0 hover:bg-ink">
                    <TableHead scope="col">Einheit</TableHead>
                    <TableHead scope="col">Mieter</TableHead>
                    <TableHead scope="col">Zeitraum</TableHead>
                    <TableHead scope="col" className="text-right">
                      Kaltmiete
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.data.tenancies.map((t) => (
                    <TableRow key={`${t.unitLabel}-${t.validFrom}`}>
                      <TableCell>
                        {t.unitLabel}
                        <span className="block text-sm text-slate">{t.areaSqm} m²</span>
                      </TableCell>
                      <TableCell>{t.renterNames.join(', ')}</TableCell>
                      <TableCell>
                        {formatDate(t.validFrom)} – {t.validTo ? formatDate(t.validTo) : 'laufend'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{t.baseRentEur}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </section>
  );
}

function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-');
  return `${day}.${month}.${year}`;
}
