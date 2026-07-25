'use client';

import type { TenancyOut } from '@/lib/contracts';

/**
 * The tenancy timeline (docs/04 M3 page 3): every row is a `validFrom/validTo`
 * period, visualized as horizontal bars over a year-gridded window. Purely
 * decorative for screen readers (aria-hidden) — the table next to it is the
 * accessible representation of the same rows.
 */

const DAY_MS = 24 * 60 * 60 * 1000;

function toDate(iso: string): number {
  return new Date(`${iso}T00:00:00Z`).getTime();
}

export function TenancyTimeline({ tenancies }: { tenancies: TenancyOut[] }) {
  if (tenancies.length === 0) return null;

  const today = Date.now();
  const start = Math.min(...tenancies.map((t) => toDate(t.validFrom)));
  const end = Math.max(
    today + 180 * DAY_MS,
    ...tenancies.map((t) => (t.validTo ? toDate(t.validTo) : today)),
  );
  const span = end - start;
  const pct = (ms: number) => Math.min(100, Math.max(0, ((ms - start) / span) * 100));

  const firstYear = new Date(start).getUTCFullYear() + 1;
  const lastYear = new Date(end).getUTCFullYear();
  const yearTicks = [];
  for (let year = firstYear; year <= lastYear; year += 1) {
    yearTicks.push({ year, at: pct(Date.UTC(year, 0, 1)) });
  }

  return (
    <div aria-hidden="true" className="select-none">
      <div className="relative h-6">
        {yearTicks.map(({ year, at }) => (
          <span
            key={year}
            style={{ left: `${at}%` }}
            className="absolute -translate-x-1/2 text-xs text-slate"
          >
            {year}
          </span>
        ))}
      </div>
      <div className="relative rounded-lg bg-mint/40 p-2">
        {yearTicks.map(({ year, at }) => (
          <span
            key={year}
            style={{ left: `${at}%` }}
            className="absolute inset-y-0 w-px bg-slate/20"
          />
        ))}
        <div className="flex flex-col gap-2">
          {tenancies.map((tenancy) => {
            const from = pct(toDate(tenancy.validFrom));
            const to = tenancy.validTo ? pct(toDate(tenancy.validTo)) : 100;
            return (
              <div key={tenancy.id} className="relative h-8">
                <div
                  style={{ left: `${from}%`, width: `${Math.max(to - from, 1.5)}%` }}
                  className={
                    'absolute inset-y-0 flex items-center overflow-hidden rounded-md px-2 ' +
                    (tenancy.activeToday ? 'bg-green' : 'bg-slate/70')
                  }
                >
                  <span className="truncate text-xs font-semibold text-white">
                    {tenancy.renterNames.join(', ')}
                    {tenancy.validTo === null ? ' →' : ''}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <p className="mt-2 text-xs text-slate">
        Grün = heute aktiv · Grau = beendet · Pfeil = unbefristet
      </p>
    </div>
  );
}
