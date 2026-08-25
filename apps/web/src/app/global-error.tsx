'use client';

import { Button } from '@lokara/ui';

import { BrandedState } from '@/features/portal/branded-state';

import { manrope, montserrat } from './fonts';
import './globals.css';

export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <html lang="de" className={`${montserrat.variable} ${manrope.variable}`}>
      <body className="bg-paper font-sans text-ink antialiased">
        <BrandedState
          title="Etwas ist schiefgelaufen"
          description="Lokara konnte gerade nicht vollständig geladen werden."
          notice="Bitte versuchen Sie es erneut."
          action={<Button onClick={reset}>Erneut versuchen</Button>}
        />
      </body>
    </html>
  );
}
