'use client';

import type { SelfUsePeriodOut, TenancyOut } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';

/**
 * The occupancy timeline (docs/04 M3 page 3) — ONE track per unit, so the gaps
 * are visible: every day is either a tenancy, an Eigennutzung period, or a
 * **Leerstand**. That gap is the whole explanation for a landlord share (the
 * canonical €181,48 of the €1.200 fixture), so it is drawn and labelled, not
 * left as whitespace.
 *
 * Decorative for screen readers (aria-hidden): the segment list below it is the
 * accessible representation, and the tenancy table repeats the same rows.
 */

const DAY_MS = 24 * 60 * 60 * 1000;

type SegmentKind = 'TENANCY' | 'SELF_USE' | 'VACANCY';

interface Segment {
  kind: SegmentKind;
  label: string;
  fromMs: number;
  toMs: number;
}

function toMs(iso: string): number {
  return new Date(`${iso}T00:00:00Z`).getTime();
}

function germanDate(ms: number): string {
  // Zero-padded dd.mm.yyyy — the same shape as isoToGermanDate elsewhere;
  // toLocaleDateString('de-DE') would render "1.7.2025" and look inconsistent
  // next to the tenancy table.
  return isoToGermanDate(new Date(ms).toISOString().slice(0, 10));
}

const KIND_STYLES: Record<SegmentKind, { bar: string; swatch: string; text: string }> = {
  TENANCY: { bar: 'bg-green', swatch: 'bg-green', text: 'text-white' },
  SELF_USE: { bar: 'bg-ink', swatch: 'bg-ink', text: 'text-white' },
  // Hatched so vacancy reads as "nothing here" without relying on colour, and
  // stays distinguishable from a dark bar for colour-blind users (BFSG).
  VACANCY: {
    bar: 'bg-warning-tint border border-dashed border-warning',
    swatch: 'bg-warning-tint border border-dashed border-warning',
    text: 'text-warning',
  },
};

/**
 * Builds the gap-filled single-track timeline. Tenancy and self-use periods are
 * taken as given (the API rejects overlaps); every uncovered day inside the
 * window becomes a Leerstand segment.
 */
export function buildSegments(
  tenancies: TenancyOut[],
  selfUsePeriods: SelfUsePeriodOut[],
  windowFromMs: number,
  windowToMs: number,
): Segment[] {
  const occupied: Segment[] = [
    ...tenancies.map((t) => ({
      kind: 'TENANCY' as const,
      label: t.renterNames.join(', '),
      fromMs: toMs(t.validFrom),
      toMs: t.validTo ? toMs(t.validTo) : windowToMs,
    })),
    ...selfUsePeriods.map((s) => ({
      kind: 'SELF_USE' as const,
      label: s.kind === 'OWNER_OCCUPIED' ? 'Eigennutzung' : 'Unentgeltlich überlassen',
      fromMs: toMs(s.validFrom),
      toMs: s.validTo ? toMs(s.validTo) : windowToMs,
    })),
  ]
    .map((segment) => ({
      ...segment,
      fromMs: Math.max(segment.fromMs, windowFromMs),
      toMs: Math.min(segment.toMs, windowToMs),
    }))
    .filter((segment) => segment.toMs > segment.fromMs)
    .sort((a, b) => a.fromMs - b.fromMs);

  const withGaps: Segment[] = [];
  let cursor = windowFromMs;
  for (const segment of occupied) {
    if (segment.fromMs > cursor) {
      withGaps.push({
        kind: 'VACANCY',
        label: 'Leerstand → Vermieter',
        fromMs: cursor,
        toMs: segment.fromMs,
      });
    }
    withGaps.push(segment);
    cursor = Math.max(cursor, segment.toMs);
  }
  if (cursor < windowToMs) {
    withGaps.push({
      kind: 'VACANCY',
      label: 'Leerstand → Vermieter',
      fromMs: cursor,
      toMs: windowToMs,
    });
  }
  return withGaps;
}

export function TenancyTimeline({
  tenancies,
  selfUsePeriods = [],
}: {
  tenancies: TenancyOut[];
  selfUsePeriods?: SelfUsePeriodOut[];
}) {
  if (tenancies.length === 0 && selfUsePeriods.length === 0) return null;

  const today = Date.now();
  const starts = [
    ...tenancies.map((t) => toMs(t.validFrom)),
    ...selfUsePeriods.map((s) => toMs(s.validFrom)),
  ];
  const ends = [
    ...tenancies.map((t) => (t.validTo ? toMs(t.validTo) : today)),
    ...selfUsePeriods.map((s) => (s.validTo ? toMs(s.validTo) : today)),
  ];
  const windowFromMs = Math.min(...starts);
  const windowToMs = Math.max(today + 180 * DAY_MS, ...ends);
  const span = windowToMs - windowFromMs;
  const pct = (ms: number) => ((ms - windowFromMs) / span) * 100;

  const segments = buildSegments(tenancies, selfUsePeriods, windowFromMs, windowToMs);

  const yearTicks: { year: number; at: number }[] = [];
  for (
    let year = new Date(windowFromMs).getUTCFullYear() + 1;
    year <= new Date(windowToMs).getUTCFullYear();
    year += 1
  ) {
    yearTicks.push({ year, at: pct(Date.UTC(year, 0, 1)) });
  }

  return (
    <div>
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
        <div className="relative h-10 overflow-hidden rounded-lg bg-mint/40">
          {yearTicks.map(({ year, at }) => (
            <span
              key={year}
              style={{ left: `${at}%` }}
              className="absolute inset-y-0 z-10 w-px bg-slate/20"
            />
          ))}
          {segments.map((segment) => {
            const left = pct(segment.fromMs);
            const width = pct(segment.toMs) - left;
            const styles = KIND_STYLES[segment.kind];
            return (
              <div
                key={`${segment.kind}-${segment.fromMs}`}
                style={{ left: `${left}%`, width: `${width}%` }}
                className={`absolute inset-y-1 flex items-center overflow-hidden rounded-md px-2 ${styles.bar}`}
              >
                <span className={`truncate text-xs font-semibold ${styles.text}`}>
                  {segment.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* The accessible representation of the same segments. */}
      <ul className="mt-3 flex flex-col gap-1.5 text-sm">
        {segments.map((segment) => {
          const styles = KIND_STYLES[segment.kind];
          return (
            <li key={`item-${segment.kind}-${segment.fromMs}`} className="flex items-start gap-2">
              <span
                aria-hidden="true"
                className={`mt-1 size-3 shrink-0 rounded-sm ${styles.swatch}`}
              />
              <span>
                <span className="font-medium">{segment.label}</span>{' '}
                <span className="text-slate">
                  ({germanDate(segment.fromMs)} – {germanDate(segment.toMs)})
                </span>
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-xs text-slate">
        Lücken sind Leerstand: diese Tage trägt der Vermieter und sie erscheinen als eigene
        Position in der Abrechnung.
      </p>
    </div>
  );
}
