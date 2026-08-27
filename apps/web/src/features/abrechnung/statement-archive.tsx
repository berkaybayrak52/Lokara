'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  StatusNote,
} from '@lokara/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';
import { useStatementHistory } from '@/features/portal/queries';
import { API_URL, ApiError } from '@/lib/api';

import { useCreateStatementDraft, useStatementRecords } from './queries';

export function StatementArchivePage({
  accountId,
  statementId,
}: {
  accountId: string;
  statementId: string;
}) {
  const router = useRouter();
  const records = useStatementRecords(accountId);
  const record = records.data?.find((entry) => entry.kind === 'FINAL' && entry.id === statementId);
  const history = useStatementHistory(accountId, record?.buildingId ?? '');
  const statement = history.data?.find((entry) => entry.id === statementId);
  const create = useCreateStatementDraft(accountId);
  const [correctionReason, setCorrectionReason] = useState('');

  if (records.isPending || (record && history.isPending)) {
    return (
      <main className="py-10">
        <div className="h-96 animate-pulse rounded-2xl bg-mint/50 motion-reduce:animate-none" />
      </main>
    );
  }
  if (!record || !statement) {
    return (
      <main className="py-10">
        <StatusNote kind="danger" label="Abrechnung nicht gefunden.">
          Öffnen Sie die gewünschte Fassung erneut aus der Abrechnungsliste.
        </StatusNote>
      </main>
    );
  }

  return (
    <main className="py-10">
      <PageHeader
        breadcrumb={
          <Link
            className="font-semibold text-green hover:underline"
            href={`/a/${accountId}/abrechnung`}
          >
            Abrechnungen
          </Link>
        }
        title={record.title}
        description={`${record.buildingName} · ${record.periodStart} bis ${record.periodEnd}`}
        status={
          <span className="rounded-full bg-mint px-3 py-1 text-sm font-semibold text-forest">
            {statement.status === 'SUPERSEDED' ? 'Korrigiert' : 'Finalisiert'} · v
            {statement.version}
          </span>
        }
      />
      <div className="grid gap-5 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Ergebnis</CardTitle>
              <CardDescription>Unveränderlich aus der finalisierten Fassung.</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="font-display text-2xl font-bold">{record.resultSummary}</p>
              <p className="mt-2 text-sm text-slate">
                Finalisiert am{' '}
                {statement.finalizedAt
                  ? new Intl.DateTimeFormat('de-DE', {
                      dateStyle: 'long',
                      timeStyle: 'short',
                    }).format(new Date(statement.finalizedAt))
                  : 'unbekannt'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Dokumente</CardTitle>
              <CardDescription>
                Downloads sind gespeicherte Archivbytes und berechnen nichts neu.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {statement.documents.map((document) => (
                <div
                  key={document.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-mint p-4"
                >
                  <div>
                    <p className="font-semibold">
                      {document.documentType === 'OWNER_OVERVIEW'
                        ? 'Vermieterübersicht'
                        : document.documentType === 'COVER_LETTER'
                          ? 'Anschreiben'
                          : 'Mieter-Einzelabrechnung'}
                    </p>
                    <p className="mt-1 text-xs text-slate">
                      SHA-256 {document.sha256.slice(0, 16)}…
                    </p>
                  </div>
                  <Button asChild size="sm" variant="outline">
                    <a
                      href={`${API_URL}/a/${accountId}/statement-documents/${document.id}/download`}
                      download
                    >
                      PDF herunterladen
                    </a>
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Versionshistorie</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {(history.data ?? [])
                .filter(
                  (entry) =>
                    entry.periodStart === statement.periodStart &&
                    entry.periodEnd === statement.periodEnd,
                )
                .map((entry) => (
                  <div key={entry.id} className="rounded-xl border border-mint p-4">
                    <p className="font-semibold">
                      Version {entry.version} ·{' '}
                      {entry.status === 'SUPERSEDED' ? 'Korrigiert' : 'Finalisiert'}
                    </p>
                    <p className="text-sm text-slate">
                      {entry.documents.length} Dokumente · alte Bytes bleiben erhalten
                    </p>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
        <div className="space-y-5">
          <StatusNote kind="warning" label="Noch nicht versendet.">
            Finalisierung ist kein Zustellnachweis. Laden Sie die PDFs herunter und versenden Sie
            sie selbst.
          </StatusNote>
          {statement.status === 'FINALIZED' ? (
            <Card>
              <CardHeader>
                <CardTitle>Korrektur erstellen</CardTitle>
                <CardDescription>
                  Die aktuelle Fassung bleibt unverändert. Eine Korrektur erzeugt einen neuen
                  Entwurf und später neue Dokumente.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Label htmlFor="correction-reason">Korrekturgrund</Label>
                <Input
                  id="correction-reason"
                  value={correctionReason}
                  onChange={(event) => setCorrectionReason(event.target.value)}
                  placeholder="Was soll korrigiert werden?"
                />
                {create.isError ? (
                  <StatusNote kind="danger" label="Korrektur konnte nicht angelegt werden.">
                    {create.error instanceof ApiError && create.error.detail
                      ? create.error.detail
                      : 'Bitte versuchen Sie es erneut.'}
                  </StatusNote>
                ) : null}
                <Button
                  disabled={!correctionReason.trim() || create.isPending}
                  onClick={() =>
                    create.mutate(
                      {
                        buildingId: record.buildingId,
                        periodStart: record.periodStart,
                        periodEnd: record.periodEnd,
                        title: `${record.title} - Korrektur`,
                        correctionOfStatementId: statement.id,
                        correctionReason,
                      },
                      {
                        onSuccess: (draft) => router.push(`/a/${accountId}/abrechnung/${draft.id}`),
                      },
                    )
                  }
                >
                  Korrektur erstellen
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </main>
  );
}
