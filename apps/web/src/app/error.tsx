'use client';

import { Button } from '@lokara/ui';

import { BrandedState } from '@/features/portal/branded-state';

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <BrandedState
      title="Etwas ist schiefgelaufen"
      description="Die angeforderte Ansicht ist gerade nicht verfügbar."
      notice="Bitte versuchen Sie es erneut."
      action={<Button onClick={reset}>Erneut versuchen</Button>}
    />
  );
}
