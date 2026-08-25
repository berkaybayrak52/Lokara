'use client';

import { Button, Card, CardDescription, CardHeader, CardTitle, StatusNote } from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';

import { useBuildingDetail, useBuildings } from '@/features/objekte/queries';

import { ReviewStep } from './review-step';
import { useStoredExtraction } from './queries';
import { UploadStep } from './upload-step';

/**
 * Beleg-Upload (docs/04 M4, canned): upload → prefill → confirm.
 *
 * The screen is a review gate, not an import. Extraction writes nothing; the
 * confirm step goes through the ordinary Kosten erfassen mutation, so a
 * prefilled entry passes exactly the checks a typed one does.
 */
export function BelegPage({ accountId }: { accountId: string }) {
  const buildings = useBuildings(accountId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const buildingId = selectedId ?? buildings.data?.buildings[0]?.id ?? null;

  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Beleg-Upload</h1>
        <p className="mt-2 max-w-prose text-slate">
          Rechnung hochladen, erkannte Felder prüfen, als Kostenart übernehmen. Gespeichert wird
          ausschließlich, was Sie bestätigt haben — eine Fehlerkennung erreicht die Abrechnung nie
          ungeprüft.
        </p>
      </header>

      {buildings.isPending ? (
        <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-mint/60" />
      ) : buildings.isError ? (
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          Laden Sie die Seite neu oder versuchen Sie es später erneut.
        </StatusNote>
      ) : buildings.data.buildings.length === 0 ? (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Noch kein Objekt</CardTitle>
            <CardDescription>
              Ein Beleg wird einem Objekt zugeordnet. Legen Sie zuerst unter{' '}
              <Link
                href={`/a/${accountId}/objekte`}
                className="text-green underline underline-offset-4"
              >
                Objekte
              </Link>{' '}
              ein Gebäude an.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          {buildings.data.buildings.length > 1 ? (
            <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Objekt wählen">
              {buildings.data.buildings.map((b) => {
                const active = b.id === buildingId;
                return (
                  <Button
                    key={b.id}
                    variant={active ? 'default' : 'outline'}
                    size="sm"
                    aria-pressed={active}
                    onClick={() => setSelectedId(b.id)}
                  >
                    {b.name}
                  </Button>
                );
              })}
            </div>
          ) : null}
          {buildingId ? <BelegForBuilding accountId={accountId} buildingId={buildingId} /> : null}
        </>
      )}
    </main>
  );
}

function BelegForBuilding({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const detail = useBuildingDetail(accountId, buildingId);
  const { extraction, runId, restored, replace, discard } = useStoredExtraction(
    accountId,
    buildingId,
  );
  const [confirmed, setConfirmed] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-8">
      <div className="max-w-xl">
        <UploadStep
          accountId={accountId}
          buildingId={buildingId}
          hasExtraction={extraction !== null}
          onExtracted={(next) => {
            setConfirmed(null);
            replace(next);
          }}
        />
      </div>

      {confirmed ? (
        <div className="max-w-xl">
          <StatusNote kind="success" label={`${confirmed} wurde übernommen.`}>
            Die Kostenart ist erfasst und fließt in die Abrechnung ein — zu sehen unter{' '}
            <Link
              href={`/a/${accountId}/kosten`}
              className="text-success underline underline-offset-4"
            >
              Kosten erfassen
            </Link>
            .
          </StatusNote>
        </div>
      ) : null}

      {extraction ? (
        <ReviewStep
          // Remount per extraction run: the form's defaults come from the
          // extraction, and RHF keeps its first set otherwise.
          key={runId ?? 'pending'}
          accountId={accountId}
          buildingId={buildingId}
          extraction={extraction}
          restored={restored}
          units={(detail.data?.units ?? []).map((u) => ({ id: u.id, label: u.label }))}
          onConfirmed={(label) => {
            setConfirmed(label);
            discard();
          }}
          onDiscard={discard}
        />
      ) : null}
    </div>
  );
}
