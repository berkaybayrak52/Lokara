import type { ReactNode } from 'react';

/**
 * Gemeinsamer Desktop-Seitenkopf (Spec 02/09 [S5]): eine `h1`, konsistente
 * Typografie und Abstände, optionale Slots für Breadcrumb, Beschreibung, Status
 * und Aktionen. Die Fachseite liefert Inhalt, dieser Kopf liefert das Layout.
 * Genau eine primäre Aktion; weitere als sekundäre Buttons rechts. Nicht sticky.
 */
export function PageHeader({
  title,
  description,
  breadcrumb,
  actions,
  status,
  titleClassName,
}: {
  title: ReactNode;
  description?: ReactNode;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
  status?: ReactNode;
  titleClassName?: string;
}) {
  return (
    <header className="mb-8">
      {breadcrumb ? <div className="mb-2 text-sm text-slate">{breadcrumb}</div> : null}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className={`font-display text-3xl font-bold text-ink ${titleClassName ?? ''}`}>
            {title}
          </h1>
          {description ? <p className="mt-2 max-w-prose text-slate">{description}</p> : null}
          {status ? <div className="mt-3">{status}</div> : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
