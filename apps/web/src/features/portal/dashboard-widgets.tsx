import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@lokara/ui';
import Link from 'next/link';

import { centsToEurDisplay } from '@/lib/format';

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
