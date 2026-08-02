'use client';

import type { CalibrationStatus } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';

/**
 * The Eichfrist guard, rendered.
 *
 * Never colour alone (BFSG): each state has its own glyph AND its own word, so
 * the badge reads identically in greyscale. NOT_APPLICABLE is deliberately
 * quiet — a Heizkostenverteiler is not eichpflichtig, so it is a fact, not a
 * warning, and dressing it as one would train people to ignore the real ones.
 */

const STYLES: Record<
  CalibrationStatus,
  { className: string; glyph: string; text: (date: string) => string }
> = {
  EXPIRED: {
    className: 'bg-danger-tint text-danger',
    glyph: '✕',
    text: (date) => `Eichfrist abgelaufen am ${date}`,
  },
  EXPIRING_SOON: {
    className: 'bg-warning-tint text-warning',
    glyph: '!',
    text: (date) => `Eichfrist endet am ${date}`,
  },
  VALID: {
    className: 'bg-success-tint text-success',
    glyph: '✓',
    text: (date) => `Geeicht bis ${date}`,
  },
  NOT_APPLICABLE: {
    className: 'bg-mint text-forest',
    glyph: '–',
    text: () => 'Nicht eichpflichtig (Heizkostenverteiler)',
  },
};

export function CalibrationBadge({
  status,
  validUntil,
}: {
  status: CalibrationStatus;
  validUntil: string | null;
}) {
  const style = STYLES[status];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${style.className}`}
    >
      <span aria-hidden="true">{style.glyph}</span>
      {style.text(validUntil ? isoToGermanDate(validUntil) : '')}
    </span>
  );
}
