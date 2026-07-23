import { Button } from '@lokara/ui';
import type { DemoSummaryResponse, HealthResponse } from '@lokara/api/contract';
import { apiClient } from '@/lib/api-client';

/**
 * M0 demo page: proves the design tokens + fonts render and that the web app
 * reaches the API through the auth guard (dev token → guarded /demo/summary).
 */

const PALETTE = [
  { name: 'Petrol Ink', token: 'ink', className: 'bg-ink', hex: '#18212A' },
  { name: 'Lokara Grün', token: 'green', className: 'bg-green', hex: '#1A6558' },
  { name: 'Forest Deep', token: 'forest', className: 'bg-forest', hex: '#123F37' },
  { name: 'Mint Tint', token: 'mint', className: 'bg-mint', hex: '#E7EFEB' },
  { name: 'Slate', token: 'slate', className: 'bg-slate', hex: '#5C6A6B' },
  { name: 'Paper', token: 'paper', className: 'bg-paper', hex: '#FBFBFA' },
] as const;

interface ApiState {
  health: HealthResponse | null;
  summary: DemoSummaryResponse | null;
  error: string | null;
}

async function loadApiState(): Promise<ApiState> {
  try {
    const health = await apiClient.health();
    const { accessToken } = await apiClient.devToken();
    const summary = await apiClient.demoSummary(accessToken);
    return { health, summary, error: null };
  } catch {
    return {
      health: null,
      summary: null,
      error:
        'API nicht erreichbar. Bitte `docker compose up -d`, `pnpm db:migrate`, `pnpm db:seed` und `pnpm dev` ausführen.',
    };
  }
}

export default async function Home() {
  const { health, summary, error } = await loadApiState();

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-12">
        <p className="mb-2 font-sans text-sm font-semibold text-green">Lokara · M0-Fundament</p>
        <h1 className="font-display text-4xl font-bold">Räume mit klarer Struktur</h1>
        <p className="mt-3 max-w-prose text-slate">
          Diese Seite belegt das M0-Skelett: Design-Tokens, Schriften (Montserrat für Headlines,
          Manrope für Text) und der Datenfluss Web-App → API → Datenbank durch den Auth-Guard.
        </p>
      </header>

      <section aria-labelledby="palette-heading" className="mb-12">
        <h2 id="palette-heading" className="mb-4 font-display text-2xl font-semibold">
          Farbpalette
        </h2>
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {PALETTE.map((color) => (
            <li key={color.token} className="overflow-hidden rounded-lg border border-mint">
              <div className={`h-16 ${color.className}`} aria-hidden="true" />
              <div className="bg-white p-3">
                <p className="font-semibold">{color.name}</p>
                <p className="text-sm text-slate">
                  {color.token} · {color.hex}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="type-heading" className="mb-12">
        <h2 id="type-heading" className="mb-4 font-display text-2xl font-semibold">
          Typografie
        </h2>
        <div className="rounded-lg bg-mint p-6">
          <p className="font-display text-3xl font-bold">Montserrat — 1.200,00 €</p>
          <p className="mt-2 font-sans">
            Manrope trägt Fließtext, Labels und Tabellen — von der Visitenkarte bis zum Dashboard.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button>Abrechnung erstellen</Button>
            <Button variant="secondary">Mehr anzeigen</Button>
          </div>
        </div>
      </section>

      <section aria-labelledby="api-heading">
        <h2 id="api-heading" className="mb-4 font-display text-2xl font-semibold">
          Live-Daten über die API
        </h2>
        {error ? (
          <p role="alert" className="rounded-lg border border-slate bg-white p-4 text-ink">
            {error}
          </p>
        ) : (
          <>
            <p className="mb-4 text-sm text-slate">
              Status: {health?.status === 'ok' ? 'API erreichbar' : 'unbekannt'} · Konto:{' '}
              {summary?.accountName} · Gebäude: {summary?.buildingAddress} ({summary?.unitCount}{' '}
              Einheiten) — geladen über den Auth-Guard.
            </p>
            <table className="w-full border-collapse overflow-hidden rounded-lg bg-white text-left">
              <caption className="sr-only">Mietverhältnisse im Demo-Gebäude</caption>
              <thead>
                <tr className="bg-ink text-paper">
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Einheit
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Mieter
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Zeitraum
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">
                    Kaltmiete
                  </th>
                </tr>
              </thead>
              <tbody>
                {summary?.tenancies.map((t) => (
                  <tr key={`${t.unitLabel}-${t.validFrom}`} className="border-t border-mint">
                    <td className="px-4 py-3">
                      {t.unitLabel}
                      <span className="block text-sm text-slate">{t.areaSqm} m²</span>
                    </td>
                    <td className="px-4 py-3">{t.renterNames.join(', ')}</td>
                    <td className="px-4 py-3">
                      {formatDate(t.validFrom)} – {t.validTo ? formatDate(t.validTo) : 'laufend'}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{t.baseRentEur}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>

      <footer className="mt-16 border-t border-mint pt-6 text-sm text-slate">
        Rechtskonform erstellt — keine Rechts- oder Steuerberatung.
      </footer>
    </main>
  );
}

function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-');
  return `${day}.${month}.${year}`;
}
