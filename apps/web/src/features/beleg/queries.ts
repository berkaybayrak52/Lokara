'use client';

import { useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';

import { api } from '@/lib/api';
import { ExtractionResponseSchema, type ExtractionResponse } from '@/lib/contracts';
import { clearFormDraft } from '@/lib/form-draft';

export const reviewDraftKey = (accountId: string, buildingId: string) =>
  `${accountId}.${buildingId}.beleg-review`;

const extractionStorageKey = (accountId: string, buildingId: string) =>
  `lokara.extraction.${accountId}.${buildingId}`;

/**
 * Upload a Beleg and get a proposal back. This writes nothing server-side —
 * the cost entry is created by the confirm step through the ordinary Kosten
 * erfassen mutation, with the same validation the manual form goes through.
 *
 * FormData deliberately carries no Content-Type header: the browser has to set
 * the multipart boundary itself.
 */
export function useExtractInvoice(accountId: string, buildingId: string) {
  return useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append('file', file);
      return api(
        `/a/${accountId}/buildings/${buildingId}/extractions`,
        ExtractionResponseSchema,
        { method: 'POST', body },
      );
    },
  });
}

/**
 * The extraction survives a reload, so the review step is not lost with it.
 *
 * The corrections live in the form draft (useFormDraft); without the
 * extraction beside them there would be no form to restore them into, and
 * "autosaved" would be a promise the page could not keep. A new upload
 * replaces both — fresh results must never be shown under stale edits.
 */
const StoredExtractionSchema = z.object({
  /** Identifies this extraction run, so the review form remounts on a new one
   * even when the (canned) values are identical. */
  runId: z.string(),
  extraction: ExtractionResponseSchema,
});
type StoredExtraction = z.infer<typeof StoredExtractionSchema>;

export function useStoredExtraction(accountId: string, buildingId: string) {
  const storageKey = extractionStorageKey(accountId, buildingId);
  const [stored, setStored] = useState<StoredExtraction | null>(null);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    setStored(null);
    setRestored(false);
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return;
    try {
      const parsed = StoredExtractionSchema.safeParse(JSON.parse(raw));
      if (parsed.success) {
        setStored(parsed.data);
        setRestored(true);
        return;
      }
    } catch {
      /* not JSON — fall through to the cleanup below */
    }
    window.localStorage.removeItem(storageKey); // stale shape — drop it
  }, [storageKey]);

  const replace = useCallback(
    (extraction: ExtractionResponse) => {
      clearFormDraft(reviewDraftKey(accountId, buildingId));
      const next: StoredExtraction = { runId: crypto.randomUUID(), extraction };
      window.localStorage.setItem(storageKey, JSON.stringify(next));
      setStored(next);
      setRestored(false);
    },
    [accountId, buildingId, storageKey],
  );

  const discard = useCallback(() => {
    clearFormDraft(reviewDraftKey(accountId, buildingId));
    window.localStorage.removeItem(storageKey);
    setStored(null);
    setRestored(false);
  }, [accountId, buildingId, storageKey]);

  return {
    extraction: stored?.extraction ?? null,
    runId: stored?.runId ?? null,
    restored,
    replace,
    discard,
  };
}
