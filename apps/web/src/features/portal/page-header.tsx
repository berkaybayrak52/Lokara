import React from 'react';

export function PageHeader({
  title,
  description,
  breadcrumb,
  status,
  actions,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  status?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-8">
      {breadcrumb ? <div className="mb-2 text-sm text-slate">{breadcrumb}</div> : null}
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-8 gap-y-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="min-w-0 break-words font-display text-3xl font-bold text-ink">
              {title}
            </h1>
            {status}
          </div>
          {description ? <p className="mt-2 max-w-prose text-slate">{description}</p> : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
