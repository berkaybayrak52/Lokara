'use client';

import { Button, Card, CardContent, CardHeader } from '@lokara/ui';

import type { RenterOverviewResponse } from '@/lib/contracts';

export type RenterOverviewViewProps = {
  state: 'loading' | 'empty' | 'error' | 'ready';
  overview?: RenterOverviewResponse;
  onRetry?: () => void;
};

export function RenterOverviewView({ state, overview, onRetry }: RenterOverviewViewProps) {
  return (
    <main className="py-12">
      <div className="mx-auto max-w-3xl">
        <h1 className="font-display text-3xl font-bold text-ink">Mein Mietverhältnis</h1>

        {state === 'loading' ? (
          <p role="status" className="mt-8 text-ink">
            Wird geladen …
          </p>
        ) : state === 'error' ? (
          <div className="mt-8 space-y-4">
            <p role="alert" className="leading-7 text-ink">
              Die Daten konnten nicht geladen werden. Bitte versuchen Sie es später erneut.
            </p>
            <Button type="button" variant="outline" onClick={onRetry}>
              Erneut versuchen
            </Button>
          </div>
        ) : state === 'empty' || overview === undefined ? (
          <p className="mt-8 max-w-xl leading-7 text-ink">
            Zu Ihrem Zugang ist derzeit kein Mietverhältnis hinterlegt. Bitte wenden Sie sich an
            Ihre Vermieterin oder Ihren Vermieter.
          </p>
        ) : (
          <Card className="mt-8">
            <CardHeader>
              <h2 className="font-display text-xl font-semibold text-ink">
                {overview.buildingName}
              </h2>
            </CardHeader>
            <CardContent>
              <address className="not-italic leading-7 text-ink">
                <span className="block">{overview.street}</span>
                <span className="block">
                  {overview.postalCode} {overview.city}
                </span>
                <span className="mt-4 block font-semibold">{overview.unitLabel}</span>
              </address>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
