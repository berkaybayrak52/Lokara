import { Button, StatusNote } from '@lokara/ui';
import Image from 'next/image';
import Link from 'next/link';
import type { ReactNode } from 'react';

export function BrandedState({
  title,
  description,
  notice,
  action,
}: {
  title: string;
  description: string;
  notice?: ReactNode;
  action: ReactNode;
}) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-xl flex-col justify-center px-6 py-16">
      <Link
        href="/"
        aria-label="Zur Lokara-Startseite"
        className="mb-10 w-fit rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
      >
        <Image src="/lokara-logo.png" alt="Lokara" width={132} height={36} priority />
      </Link>
      <h1 className="font-display text-3xl font-bold text-ink">{title}</h1>
      <p className="mt-3 max-w-prose text-slate">{description}</p>
      {notice ? (
        <div className="mt-6">
          <StatusNote kind="danger" label="Die Seite konnte nicht angezeigt werden.">
            {notice}
          </StatusNote>
        </div>
      ) : null}
      <div className="mt-8">{action}</div>
    </main>
  );
}

export function OverviewLink() {
  return (
    <Button asChild>
      <Link href="/">Zur Übersicht</Link>
    </Button>
  );
}
