'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@lokara/ui';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { centsToEurDisplay } from '@/lib/format';

import type { DemoCashflowMonth } from './dashboard-demo';

export function MietSollCard({
  buildingCount,
  mietSollCentsMonthly,
}: {
  buildingCount: number;
  mietSollCentsMonthly: number;
}) {
  return (
    <Card className="min-w-0 overflow-hidden border-l-4 border-green">
      <CardHeader>
        <CardDescription className="font-semibold text-forest">
          Mietsoll · monatlich
        </CardDescription>
        <CardTitle className="break-words font-display text-3xl tabular-nums text-ink">
          {mietSollCentsMonthly > 0
            ? centsToEurDisplay(mietSollCentsMonthly)
            : 'Noch keine aktive Kaltmiete'}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate">
        Monatliche Kaltmiete aus {buildingCount === 1 ? 'einem Objekt' : `${buildingCount} Objekten`}.
      </CardContent>
    </Card>
  );
}

export function OccupancyCard({
  accountId,
  href,
  occupiedUnitCount,
  vacantUnitCount,
  unitCount,
}: {
  accountId: string;
  href?: string;
  occupiedUnitCount: number;
  vacantUnitCount: number;
  unitCount: number;
}) {
  if (unitCount === 0) {
    return (
      <Card className="min-w-0 overflow-hidden border-l-4 border-green">
        <CardHeader>
          <CardDescription className="font-semibold text-forest">
            Einheiten vermietet
          </CardDescription>
          <CardTitle className="font-display text-xl text-ink">Noch keine Einheiten</CardTitle>
        </CardHeader>
        <CardContent>
          <Link
            href={href ?? `/a/${accountId}/objekte`}
            className="rounded-sm text-sm font-semibold text-forest underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2"
          >
            Erste Einheit anlegen
          </Link>
        </CardContent>
      </Card>
    );
  }

  const percent = Math.min(100, Math.round((occupiedUnitCount / unitCount) * 100));
  const circumference = 175.93;

  return (
    <Link
      href={href ?? `/a/${accountId}/objekte`}
      className="min-w-0 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2"
      aria-label={`Objektliste öffnen: ${occupiedUnitCount} von ${unitCount} Einheiten vermietet`}
    >
      <Card className="h-full min-w-0 overflow-hidden border-l-4 border-green transition-transform duration-200 ease-out hover:-translate-y-0.5 motion-reduce:transform-none">
        <CardContent className="flex min-w-0 items-center gap-4 pt-6">
          <svg
            viewBox="0 0 72 72"
            className="h-20 w-20 shrink-0"
            role="img"
            aria-label={`${occupiedUnitCount} von ${unitCount} Einheiten vermietet, ${percent} %`}
          >
            <circle
              cx="36"
              cy="36"
              r="28"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              className="text-mint"
            />
            <circle
              cx="36"
              cy="36"
              r="28"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - percent / 100)}
              className="origin-center -rotate-90 text-green"
            />
          </svg>
          <div className="min-w-0">
            <p className="font-semibold text-forest">Einheiten vermietet</p>
            <p className="font-display text-3xl tabular-nums text-ink">
              {occupiedUnitCount} / {unitCount}
            </p>
            <p className="mt-1 text-sm text-slate">
              {vacantUnitCount === 0
                ? 'Voll vermietet'
                : `${vacantUnitCount} ${vacantUnitCount === 1 ? 'Einheit' : 'Einheiten'} frei`}
            </p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export function UnavailableCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="min-w-0 overflow-hidden">
      <CardHeader>
        <CardDescription className="font-semibold text-forest">{title}</CardDescription>
        <CardTitle className="font-display text-xl text-ink">Noch nicht verfügbar</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate">{description}</CardContent>
    </Card>
  );
}

export function DashboardSkeleton() {
  return (
    <div role="status" aria-busy="true" className="min-w-0 overflow-hidden">
      <span className="sr-only">Übersicht wird geladen</span>
      <div aria-hidden="true">
        <div className="grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              className="h-40 min-w-0 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
          ))}
        </div>
        <div className="mt-6 grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              className="h-32 min-w-0 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
          ))}
        </div>
      </div>
    </div>
  );
}

const RING_CIRCUMFERENCE = 175.93;

/** SVG-Fortschrittsring: Spur in Mint, gefüllter Bogen in Grün. Nenner 0 → leer. */
function ProgressRing({ percent, label }: { percent: number; label: string }) {
  return (
    <svg viewBox="0 0 72 72" className="h-20 w-20 shrink-0" role="img" aria-label={label}>
      <circle cx="36" cy="36" r="28" fill="none" stroke="currentColor" strokeWidth="8" className="text-mint" />
      <circle
        cx="36"
        cy="36"
        r="28"
        fill="none"
        stroke="currentColor"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={RING_CIRCUMFERENCE}
        strokeDashoffset={RING_CIRCUMFERENCE * (1 - percent / 100)}
        className="origin-center -rotate-90 text-green"
      />
    </svg>
  );
}

/**
 * KPI-Karte mit Ring (Spec [D4]). Der Ring füllt sich nach Zähler/Nenner
 * (gedeckelt 100 %); bei Nenner 0 bleibt er leer. Marken-Akzent aus 00 A5.
 */
export function RingKpiCard({
  label,
  valueText,
  numerator,
  denominator,
  sublabel,
}: {
  label: string;
  valueText: string;
  numerator: number;
  denominator: number;
  sublabel: string;
}) {
  const percent = denominator > 0 ? Math.min(100, Math.round((numerator / denominator) * 100)) : 0;
  return (
    <Card className="h-full min-w-0 overflow-hidden border-l-4 border-green">
      <CardContent className="flex h-full min-w-0 items-center gap-4 pt-6">
        <ProgressRing percent={percent} label={`${label}: ${percent} %`} />
        <div className="min-w-0">
          <p className="font-semibold text-forest">{label}</p>
          <p className="break-words font-display text-3xl tabular-nums text-ink">{valueText}</p>
          <p className="mt-1 text-sm text-slate">{sublabel}</p>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * KPI-Karte ohne Ring (Spec [D4], Offene Posten): absoluter Betrag ohne Nenner.
 * Gleiche vertikale Rhythmik wie die Ring-Karten (ein zentrierter Textblock,
 * kein auseinandergezogener Header/Content), damit die obere Reihe konsistent
 * wirkt.
 */
export function PlainKpiCard({
  label,
  valueText,
  sublabel,
}: {
  label: string;
  valueText: string;
  sublabel: string;
}) {
  return (
    <Card className="h-full min-w-0 overflow-hidden border-l-4 border-green">
      <CardContent className="flex h-full min-w-0 items-center pt-6">
        <div className="min-w-0">
          <p className="font-semibold text-forest">{label}</p>
          <p className="break-words font-display text-3xl tabular-nums text-ink">{valueText}</p>
          <p className="mt-1 text-sm text-slate">{sublabel}</p>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Aufgaben-/Ticket-Zählerleiste (Spec [D6]). Überfällig zuerst und am lautesten,
 * jeweils Zahl UND Wortlabel (BFSG). Kein Board, keine Navigation.
 *
 * TODO(ticket-spec): Zähler und Klickziel später an das Ticket-System-Spec
 * anbinden und diesen Mock ersetzen.
 */
export function TasksBar({
  overdue,
  today,
  week,
}: {
  overdue: number;
  today: number;
  week: number;
}) {
  return (
    <Card className="min-w-0 overflow-hidden">
      <CardHeader>
        <CardTitle>Aufgaben &amp; Tickets</CardTitle>
        <CardDescription>Aus Mieter-Tickets &amp; eigenen Aufgaben.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-wrap items-baseline gap-x-8 gap-y-3">
          <li className="flex items-baseline gap-2 font-semibold text-danger">
            <span className="font-display text-2xl tabular-nums">{overdue}</span>
            <span>überfällig</span>
          </li>
          <li className="flex items-baseline gap-2 text-ink">
            <span className="font-display text-2xl tabular-nums">{today}</span>
            <span>heute fällig</span>
          </li>
          <li className="flex items-baseline gap-2 text-slate">
            <span className="font-display text-2xl tabular-nums">{week}</span>
            <span>diese Woche fällig</span>
          </li>
        </ul>
      </CardContent>
    </Card>
  );
}

type CashflowView = 'jahr' | 'quartal' | 'monat';

const VIEW_LABELS: Record<CashflowView, string> = {
  jahr: 'Jahr',
  quartal: 'Quartal',
  monat: 'Monat',
};

function aggregate(months: DemoCashflowMonth[], view: CashflowView): DemoCashflowMonth[] {
  if (view === 'jahr') return months;
  if (view === 'monat') {
    const last = months[months.length - 1];
    return last ? [last] : [];
  }
  // Quartal: je drei aufeinanderfolgende Monate summieren.
  const quarters: DemoCashflowMonth[] = [];
  for (let q = 0; q < months.length; q += 3) {
    const slice = months.slice(q, q + 3);
    if (slice.length === 0) continue;
    const inCents = slice.reduce((s, m) => s + m.inCents, 0);
    const outCents = slice.reduce((s, m) => s + m.outCents, 0);
    quarters.push({
      label: `Q${quarters.length + 1}`,
      inCents,
      outCents,
      surplusCents: inCents - outCents,
    });
  }
  return quarters;
}


/**
 * Cashflow-Widget (Spec [D5]): gruppierte Senkrechtbalken (Einnahmen grün,
 * Ausgaben Slate) als HTML mit fester Balkenbreite — dadurch KEINE Verzerrung
 * bei wenigen Gruppen (Quartal/Monat). Darüber die Überschuss-Linie als
 * Overlay-SVG (non-scaling-stroke). Beim Umschalten Jahr/Quartal/Monat wachsen
 * die Balken animiert von unten (respektiert prefers-reduced-motion). Keine
 * Diagramm-Bibliothek. Überschrifts-Kennzahl, Legende, Tooltip, Umschalter.
 */
export function CashflowWidget({ months }: { months: DemoCashflowMonth[] }) {
  const [view, setView] = useState<CashflowView>('jahr');
  const [hovered, setHovered] = useState<number | null>(null);
  const groups = useMemo(() => aggregate(months, view), [months, view]);

  const currentSurplus = months[months.length - 1]?.surplusCents ?? 0;
  const max = Math.max(1, ...groups.map((g) => Math.max(g.inCents, g.outCents)));

  const PLOT_H = 180;
  const heightPct = (cents: number) => `${Math.max(1.5, (cents / max) * 100)}%`;
  const surplusTop = (cents: number) => 100 - Math.max(0, Math.min(100, (cents / max) * 100));
  const centerLeft = (i: number) => `${((i + 0.5) / groups.length) * 100}%`;
  const linePoints = groups.map((g, i) => `${((i + 0.5) / groups.length) * 100},${surplusTop(g.surplusCents)}`).join(' ');

  return (
    <Card className="min-w-0 overflow-hidden">
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-semibold text-forest">Überschuss · lfd. Monat</p>
            <p className="font-display text-3xl tabular-nums text-ink">
              {centsToEurDisplay(currentSurplus)}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <ul className="hidden items-center gap-3 text-xs text-slate sm:flex">
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-green" />Einnahmen
              </li>
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-slate" />Ausgaben
              </li>
              <li className="flex items-center gap-1.5">
                <span className="h-0.5 w-3 rounded bg-forest" />Überschuss
              </li>
            </ul>
            <div className="flex rounded-lg border border-mint p-0.5" role="group" aria-label="Zeitraum">
              {(['jahr', 'quartal', 'monat'] as CashflowView[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={view === option}
                  onClick={() => {
                    setView(option);
                    setHovered(null);
                  }}
                  className={`rounded-md px-3 py-1 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green ${
                    view === option ? 'bg-green text-white' : 'text-slate hover:text-ink'
                  }`}
                >
                  {VIEW_LABELS[option]}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="relative mt-4">
          {/* Balken als HTML: feste Breite, zentriert je Gruppe → keine Verzerrung. */}
          <div className="flex items-end gap-1.5 sm:gap-2" style={{ height: PLOT_H }}>
            {groups.map((g, i) => (
              <div
                key={`${view}-${g.label}`}
                className="flex h-full flex-1 items-end justify-center gap-1"
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered((prev) => (prev === i ? null : prev))}
              >
                <div
                  data-anim
                  className="w-3 rounded-t bg-green sm:w-4"
                  style={{ height: heightPct(g.inCents), transformOrigin: 'bottom', animationDelay: `${i * 35}ms` }}
                />
                <div
                  data-anim
                  className="w-3 rounded-t bg-slate sm:w-4"
                  style={{ height: heightPct(g.outCents), transformOrigin: 'bottom', animationDelay: `${i * 35 + 60}ms` }}
                />
              </div>
            ))}
          </div>

          {/* Überschuss-Linie als Overlay; Strichstärke bleibt konstant. */}
          <svg
            key={`line-${view}`}
            className="cashflow-line pointer-events-none absolute inset-x-0 top-0"
            width="100%"
            height={PLOT_H}
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <polyline
              points={linePoints}
              fill="none"
              className="stroke-forest"
              strokeWidth={2}
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          {/* Überschuss-Punkte als HTML, damit sie kreisrund bleiben. */}
          <div className="pointer-events-none absolute inset-x-0 top-0" style={{ height: PLOT_H }}>
            {groups.map((g, i) => (
              <span
                key={`dot-${view}-${g.label}`}
                className="absolute h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-forest"
                style={{ left: centerLeft(i), top: `${surplusTop(g.surplusCents)}%` }}
              />
            ))}
          </div>

          {hovered !== null && groups[hovered] ? (
            <div
              className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 rounded-lg border border-mint bg-white px-3 py-2 text-xs shadow-sm"
              style={{ left: centerLeft(hovered) }}
              role="status"
            >
              <p className="font-semibold text-ink">{groups[hovered].label}</p>
              <p className="text-slate">Einnahmen {centsToEurDisplay(groups[hovered].inCents)}</p>
              <p className="text-slate">Ausgaben {centsToEurDisplay(groups[hovered].outCents)}</p>
              <p className="font-medium text-forest">
                Überschuss {centsToEurDisplay(groups[hovered].surplusCents)}
              </p>
            </div>
          ) : null}
        </div>

        {/* Beschriftungen als HTML → immer scharf, nie gestreckt. */}
        <div className="mt-2 flex gap-1.5 sm:gap-2">
          {groups.map((g) => (
            <div key={`lbl-${view}-${g.label}`} className="flex-1 text-center text-xs text-slate">
              {g.label}
            </div>
          ))}
        </div>

        <p className="mt-3 text-sm text-slate">
          Demonstrationswerte, aus dem monatlichen Mietsoll abgeleitet.
        </p>
      </CardContent>
    </Card>
  );
}
