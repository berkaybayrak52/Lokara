'use client';

import { Button, Card, CardContent, CardHeader } from '@lokara/ui';

import { API_URL } from '@/lib/api';
import type { RenterPortalPublication } from '@/lib/contracts';

import { useRenterPublications } from './queries';

type DocumentKind = 'STATEMENT_ARCHIVE' | 'UVI_ARTIFACT';

export type RenterDocumentsViewProps = {
  kind: DocumentKind;
  state: 'loading' | 'empty' | 'error' | 'ready';
  documents?: RenterPortalPublication[];
  downloadBaseUrl?: string;
  onRetry?: () => void;
};

const MONTH_NAMES = [
  'Januar',
  'Februar',
  'März',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
] as const;

function parseDateParts(value: string): { year: number; month: number; day: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return { year, month, day };
}

function formatDate(value: string): string | null {
  const date = parseDateParts(value);
  if (!date) return null;
  return `${String(date.day).padStart(2, '0')}.${String(date.month).padStart(2, '0')}.${date.year}`;
}

function publicationTitle(document: RenterPortalPublication): string | null {
  if (
    document.sourceKind === 'STATEMENT_ARCHIVE' &&
    document.periodStart !== null &&
    document.periodEnd !== null
  ) {
    const start = formatDate(document.periodStart);
    const end = formatDate(document.periodEnd);
    return start && end ? `Abrechnung ${start}–${end}` : null;
  }
  if (document.sourceKind === 'UVI_ARTIFACT' && document.documentMonth !== null) {
    const month = parseDateParts(document.documentMonth);
    if (!month || month.day !== 1) return null;
    const monthName = MONTH_NAMES[month.month - 1];
    return monthName ? `Verbrauchsinformation ${monthName} ${month.year}` : null;
  }
  return null;
}

function safeDownloadPath(document: RenterPortalPublication): string | null {
  const expected = `/renter/${encodeURIComponent(document.tenancyId)}/documents/${encodeURIComponent(document.id)}/download`;
  return document.downloadUrl === expected ? expected : null;
}

function downloadHref(document: RenterPortalPublication, baseUrl: string): string | null {
  const path = safeDownloadPath(document);
  if (!path) return null;
  return baseUrl === '' ? path : `${baseUrl.replace(/\/$/, '')}${path}`;
}

export function RenterDocumentsView({
  kind,
  state,
  documents = [],
  downloadBaseUrl = '',
  onRetry,
}: RenterDocumentsViewProps) {
  const heading = kind === 'STATEMENT_ARCHIVE' ? 'Abrechnungen' : 'Verbrauchsinformationen';
  const matchingDocuments = documents.filter((document) => document.sourceKind === kind);
  const emptyCopy =
    kind === 'STATEMENT_ARCHIVE'
      ? 'Es liegen noch keine Abrechnungen für Sie bereit.'
      : 'Es liegen noch keine Verbrauchsinformationen für Sie bereit.';

  return (
    <main className="py-12">
      <div className="mx-auto max-w-3xl">
        <h1 className="font-display text-3xl font-bold text-ink">{heading}</h1>

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
        ) : state === 'empty' || matchingDocuments.length === 0 ? (
          <p className="mt-8 leading-7 text-ink">{emptyCopy}</p>
        ) : (
          <ul className="mt-8 space-y-4">
            {matchingDocuments.map((document) => {
              const title = publicationTitle(document);
              const href = downloadHref(document, downloadBaseUrl);
              if (!title) return null;
              return (
                <li key={document.id}>
                  <Card>
                    <CardHeader>
                      <h2 className="font-display text-xl font-semibold text-ink">{title}</h2>
                    </CardHeader>
                    {href ? (
                      <CardContent>
                        <Button asChild variant="outline">
                          <a href={href}>Als PDF speichern</a>
                        </Button>
                      </CardContent>
                    ) : null}
                  </Card>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </main>
  );
}

export function RenterDocumentsScreen({
  tenancyId,
  kind,
}: {
  tenancyId: string;
  kind: DocumentKind;
}) {
  const publications = useRenterPublications(tenancyId);
  if (publications.isPending) return <RenterDocumentsView kind={kind} state="loading" />;
  if (publications.isError) {
    return (
      <RenterDocumentsView kind={kind} state="error" onRetry={() => void publications.refetch()} />
    );
  }
  const documents = publications.data.documents.filter((document) => document.sourceKind === kind);
  return (
    <RenterDocumentsView
      kind={kind}
      state={documents.length === 0 ? 'empty' : 'ready'}
      documents={documents}
      downloadBaseUrl={API_URL}
    />
  );
}
