'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@lokara/ui';
import Link from 'next/link';

import type { BuildingDashboardFact } from '@/lib/contracts';

/**
 * "Aufmerksamkeit" (OD7): at most three facts the backend already decided are
 * relevant, in the order it gave them. No severity, ranking or word like
 * "dringend" is invented here, and an empty box is a calm positive state.
 */
export function BuildingAttention({
  facts,
  factsTotal,
}: {
  facts: BuildingDashboardFact[];
  factsTotal: number;
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Aufmerksamkeit</CardTitle>
      </CardHeader>
      <CardContent>
        {facts.length === 0 ? (
          <div>
            <p className="font-semibold text-ink">Alles im Blick</p>
            <p className="mt-1 text-sm text-slate">
              Für dieses Objekt besteht aktuell kein Handlungsbedarf.
            </p>
          </div>
        ) : (
          <ul className="flex flex-col gap-4">
            {facts.map((fact) => (
              <li key={fact.id} className="border-b border-mint pb-4 last:border-b-0 last:pb-0">
                <p className="font-semibold text-ink">
                  {fact.text}
                  {fact.severity === 'attention' ? (
                    <span className="ml-2 text-xs font-normal text-slate">Offener Betrag</span>
                  ) : null}
                </p>
                {fact.unitLabel ? <p className="text-sm text-slate">{fact.unitLabel}</p> : null}
                {fact.actionHref && fact.actionLabel ? (
                  <Link
                    href={fact.actionHref}
                    className="mt-1 inline-block text-sm text-green underline-offset-4 hover:underline"
                  >
                    {fact.actionLabel}
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {factsTotal > facts.length ? (
          <p className="mt-4 text-xs text-slate">
            {factsTotal - facts.length} weitere Hinweise sind in den Fachbereichen sichtbar.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
