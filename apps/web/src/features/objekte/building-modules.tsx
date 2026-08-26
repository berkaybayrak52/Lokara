'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@lokara/ui';
import Link from 'next/link';

import type { BuildingDashboardModule } from '@/lib/contracts';

/**
 * Compact module summaries (OD11). Each card shows at most three server-owned
 * figures and one drill-down; no full history is loaded here, and a module that
 * has no data source says so instead of showing a zero.
 */
export function BuildingModules({ modules }: { modules: BuildingDashboardModule[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {modules.map((module) => (
        <Card key={module.key}>
          <CardHeader>
            <CardTitle>{module.title}</CardTitle>
          </CardHeader>
          <CardContent>
            {module.available ? (
              <dl className="flex flex-col gap-2">
                {module.facts.map((fact) => (
                  <div key={fact.label} className="flex items-baseline justify-between gap-4">
                    <dt className="text-sm text-slate">{fact.label}</dt>
                    <dd className="text-right font-semibold tabular-nums text-ink">{fact.value}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-slate">{module.unavailableReason}</p>
            )}
            {module.actionHref && module.actionLabel ? (
              <Link
                href={module.actionHref}
                className="mt-4 inline-block text-sm text-green underline-offset-4 hover:underline"
              >
                {module.actionLabel}
              </Link>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
