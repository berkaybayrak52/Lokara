'use client';

import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Label, StatusNote } from '@lokara/ui';
import { useRef, useState } from 'react';

import { ApiError } from '@/lib/api';
import type { ExtractionResponse } from '@/lib/contracts';

import { useExtractInvoice } from './queries';

const ACCEPT = '.pdf,.png,.jpg,.jpeg';

/** Step 1 of docs/04 page 7: upload → prefill → confirm. */
export function UploadStep({
  accountId,
  buildingId,
  hasExtraction,
  onExtracted,
}: {
  accountId: string;
  buildingId: string;
  hasExtraction: boolean;
  onExtracted: (extraction: ExtractionResponse) => void;
}) {
  const extract = useExtractInvoice(accountId, buildingId);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    extract.mutate(file, {
      onSuccess: (extraction) => {
        onExtracted(extraction);
        setFile(null);
        if (inputRef.current) inputRef.current.value = '';
      },
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Beleg hochladen</CardTitle>
        <CardDescription>
          PDF, PNG oder JPG bis 10 MB. Die erkannten Felder werden anschließend zur Prüfung
          angezeigt — gespeichert wird erst nach Ihrer Bestätigung.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="beleg-file">Rechnung auswählen</Label>
            <input
              ref={inputRef}
              id="beleg-file"
              type="file"
              accept={ACCEPT}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-slate bg-white px-3 py-2 font-sans text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-mint file:px-3 file:py-1.5 file:font-sans file:text-sm file:font-semibold file:text-ink hover:file:bg-mint/80 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring"
            />
            <p className="text-sm text-slate">
              {file ? `Ausgewählt: ${file.name}` : 'Noch keine Datei ausgewählt.'}
            </p>
          </div>
          <div>
            <Button type="submit" disabled={!file || extract.isPending}>
              {extract.isPending ? 'Wird ausgelesen…' : 'Beleg auslesen'}
            </Button>
          </div>
          {hasExtraction ? (
            <StatusNote kind="warning" label="Ein Beleg wird bereits geprüft.">
              Ein neuer Upload ersetzt die aktuelle Prüfung samt Ihrer Korrekturen.
            </StatusNote>
          ) : null}
          {extract.isError ? (
            <StatusNote kind="danger" label="Auslesen fehlgeschlagen.">
              {extract.error instanceof ApiError && extract.error.detail
                ? extract.error.detail
                : 'Bitte erneut versuchen.'}
            </StatusNote>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}
