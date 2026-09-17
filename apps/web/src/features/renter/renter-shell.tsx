'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import type { MeAccount } from '@/lib/contracts';

import { useRenterContextOverviews, useRenterMe } from './queries';

type LabeledRenterContext = {
  tenancyId: string;
  street: string;
  unitLabel: string;
};

export type RenterShellContentProps = {
  tenancyId: string;
  pathname: string;
  accounts: MeAccount[];
  renterContexts: LabeledRenterContext[];
  contextCount?: number;
  children: ReactNode;
};

const renterNavigation = [
  { suffix: '', label: 'Mein Mietverhältnis' },
  { suffix: '/abrechnungen', label: 'Abrechnungen' },
  { suffix: '/verbrauchsinformationen', label: 'Verbrauchsinformationen' },
] as const;

export function RenterShellContent({
  tenancyId,
  pathname,
  accounts,
  renterContexts,
  contextCount,
  children,
}: RenterShellContentProps) {
  const totalContexts = contextCount ?? accounts.length + renterContexts.length;
  const showSwitcher = totalContexts > 1;
  const currentContext = renterContexts.find((context) => context.tenancyId === tenancyId);

  return (
    <div className="min-h-dvh bg-paper text-ink">
      <header className="border-b border-mint bg-white">
        <div className="mx-auto flex min-h-16 w-full min-w-0 max-w-[1440px] flex-wrap items-center justify-between gap-4 px-6 min-[1440px]:px-8">
          <p className="min-w-0 font-display text-xl font-bold text-forest [overflow-wrap:anywhere]">Meine Unterlagen</p>
          {showSwitcher ? (
            <details className="relative min-w-0 max-w-full">
              <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-slate px-4 py-2 text-sm font-semibold text-ink transition-colors duration-150 ease-out hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none">
                <span className="min-w-0 [overflow-wrap:anywhere]">
                  {currentContext
                    ? `Mietverhältnis — ${currentContext.street}, ${currentContext.unitLabel}`
                    : 'Meine Unterlagen'}
                </span>
                <svg
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                  className="size-4 shrink-0 fill-current"
                >
                  <path d="m5.25 7.75 4.75 4.5 4.75-4.5" />
                </svg>
              </summary>
              <div className="absolute right-0 z-20 mt-2 w-80 max-w-full rounded-xl bg-white p-4 shadow-sm [overflow-wrap:anywhere]">
                {accounts.length > 0 ? (
                  <ul aria-label="Meine Unterlagen" className="mb-4 space-y-1">
                    {accounts.map((account) => (
                      <li key={account.id}>
                        <Link
                          href={`/a/${account.id}`}
                          className="block rounded-lg px-3 py-2 text-sm text-ink transition-colors duration-150 ease-out hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none"
                        >
                          {account.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <p className="mb-2 text-sm font-semibold text-forest">Als Mieter</p>
                <ul className="space-y-1">
                  {renterContexts.map((context) => (
                    <li key={context.tenancyId}>
                      <Link
                        className="block rounded-lg px-3 py-2 text-sm text-ink [overflow-wrap:anywhere] transition-colors duration-150 ease-out hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none"
                        href={`/renter/${context.tenancyId}`}
                        aria-current={context.tenancyId === tenancyId ? 'page' : undefined}
                      >
                        Mietverhältnis — {context.street}, {context.unitLabel}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          ) : null}
        </div>
      </header>

      <div className="mx-auto w-full max-w-[1440px] px-6 min-[1440px]:px-8">
        <nav aria-label="Meine Unterlagen" className="border-b border-mint py-3">
          <ul className="flex flex-wrap gap-2">
            {renterNavigation.map((item) => {
              const href = `/renter/${tenancyId}${item.suffix}`;
              const active = pathname === href;
              return (
                <li key={href} className="min-w-0 max-w-full">
                  <Link
                    href={href}
                    aria-current={active ? 'page' : undefined}
                    className={
                      'block max-w-full rounded-lg px-3 py-2 text-sm font-semibold [overflow-wrap:anywhere] transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none ' +
                      (active ? 'bg-mint text-forest' : 'text-ink hover:bg-mint/60')
                    }
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        {children}
      </div>
    </div>
  );
}

export function RenterShell({ tenancyId, children }: { tenancyId: string; children: ReactNode }) {
  const pathname = usePathname();
  const me = useRenterMe();
  const rawContexts = me.data?.renterContexts ?? [];
  const overviews = useRenterContextOverviews(rawContexts.map((context) => context.tenancyId));
  const renterContexts = overviews.flatMap((overview) =>
    overview.data
      ? [
          {
            tenancyId: overview.data.tenancyId,
            street: overview.data.street,
            unitLabel: overview.data.unitLabel,
          },
        ]
      : [],
  );

  return (
    <RenterShellContent
      tenancyId={tenancyId}
      pathname={pathname}
      accounts={me.data?.accounts ?? []}
      renterContexts={renterContexts}
      contextCount={(me.data?.accounts.length ?? 0) + rawContexts.length}
    >
      {children}
    </RenterShellContent>
  );
}
