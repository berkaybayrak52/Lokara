'use client';

import { useEffect, useState } from 'react';
import type { FieldValues, UseFormReturn } from 'react-hook-form';

/**
 * Autosave / no data loss on abort (docs/04, non-negotiable): every form
 * keystroke is mirrored to localStorage; closing the tab, navigating away or
 * a crash loses nothing — the draft is restored on return and only a
 * successful submit clears it. Server-side drafts arrive with real accounts;
 * the storage key is account-scoped so drafts never bleed across contexts.
 */
export function useFormDraft<T extends FieldValues>(
  key: string,
  form: UseFormReturn<T>,
): { draftRestored: boolean; clearDraft: () => void } {
  const storageKey = `lokara.draft.${key}`;
  const [draftRestored, setDraftRestored] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) {
        form.reset(JSON.parse(raw) as T, { keepDefaultValues: true });
        setDraftRestored(true);
      }
    } catch {
      window.localStorage.removeItem(storageKey); // corrupt draft — drop it
    }
    // subscribe (not watch): fires on every value change without re-rendering.
    return form.subscribe({
      formState: { values: true },
      callback: ({ values }) => {
        window.localStorage.setItem(storageKey, JSON.stringify(values));
      },
    });
  }, [form, storageKey]);

  return {
    draftRestored,
    clearDraft: () => {
      window.localStorage.removeItem(storageKey);
      setDraftRestored(false);
    },
  };
}
