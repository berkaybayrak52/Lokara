'use client';

import { Button, Card, CardContent, CardHeader, Input, Label } from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';

import { ApiError } from '@/lib/api';

import { useActivateRenterAccess, useRenterOverview } from './queries';
import { RenterOverviewView } from './renter-overview';

const REFUSAL_COPY =
  'Die Aktivierung war nicht möglich. Bitte prüfen Sie den Code oder wenden Sie sich an Ihre Vermieterin oder Ihren Vermieter.';

export type RenterActivationViewProps = {
  state: 'entry' | 'success' | 'refused';
  tenancyId?: string;
  activationCode?: string;
  isPending?: boolean;
  onActivationCodeChange?: (value: string) => void;
  onActivate?: () => void;
};

export function RenterActivationView({
  state,
  tenancyId,
  activationCode = '',
  isPending = false,
  onActivationCodeChange,
  onActivate,
}: RenterActivationViewProps) {
  if (state === 'success') {
    return (
      <Card className="mx-auto mt-12 max-w-2xl">
        <CardHeader>
          <h1 className="font-display text-3xl font-bold text-ink">Ihr Zugang ist aktiviert.</h1>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="max-w-xl leading-7 text-ink">
            Sie sehen hier künftig Ihre Abrechnungen und Ihre monatlichen Verbrauchsinformationen,
            sobald Ihre Vermieterin oder Ihr Vermieter sie bereitstellt.
          </p>
          {tenancyId ? (
            <Button asChild>
              <Link href={`/renter/${tenancyId}`}>Zu meinen Unterlagen</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto mt-12 max-w-2xl">
      <CardHeader>
        <h1 className="font-display text-3xl font-bold text-ink">Mieterzugang aktivieren</h1>
      </CardHeader>
      <CardContent>
        <p className="mb-6 max-w-xl leading-7 text-ink">
          Geben Sie den Aktivierungscode ein, den Sie von Ihrer Vermieterin oder Ihrem Vermieter
          erhalten haben. Der Code gilt einmalig.
        </p>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            onActivate?.();
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="renter-activation-code">Aktivierungscode</Label>
            <Input
              id="renter-activation-code"
              autoComplete="one-time-code"
              value={activationCode}
              aria-invalid={state === 'refused'}
              aria-describedby={state === 'refused' ? 'renter-activation-refusal' : undefined}
              onChange={(event) => onActivationCodeChange?.(event.currentTarget.value)}
            />
          </div>
          {state === 'refused' ? (
            <p
              id="renter-activation-refusal"
              role="alert"
              className="rounded-lg bg-danger-tint p-4 text-sm leading-6 text-danger"
            >
              {REFUSAL_COPY}
            </p>
          ) : null}
          <Button type="submit" disabled={isPending}>
            Zugang aktivieren
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export function RenterOverviewScreen({ tenancyId }: { tenancyId: string }) {
  const [activationCode, setActivationCode] = useState('');
  const overview = useRenterOverview(tenancyId);
  const activation = useActivateRenterAccess(tenancyId);

  if (activation.isSuccess) {
    return <RenterActivationView state="success" tenancyId={tenancyId} />;
  }

  if (overview.isPending) {
    return <RenterOverviewView state="loading" />;
  }

  if (overview.isError) {
    if (overview.error instanceof ApiError && overview.error.status === 404) {
      return (
        <RenterActivationView
          state={activation.isError ? 'refused' : 'entry'}
          activationCode={activationCode}
          isPending={activation.isPending}
          onActivationCodeChange={(value) => {
            setActivationCode(value);
            if (activation.isError) activation.reset();
          }}
          onActivate={() => activation.mutate(activationCode)}
        />
      );
    }
    return <RenterOverviewView state="error" onRetry={() => void overview.refetch()} />;
  }

  return <RenterOverviewView state="ready" overview={overview.data} />;
}
