/**
 * German-format numeric input parsing — at the FORM boundary only.
 * Money crosses the wire as integer cents, areas as m² × 100 (docs/02);
 * floats never touch either. Parsing returns null for anything ambiguous —
 * a form shows an error instead of guessing.
 */

/** "950", "950,5", "950,50", "1.234,56" → cents. Max 2 decimal places. */
export function parseEurToCents(raw: string): number | null {
  const normalized = raw.trim().replace(/\s|€/g, '');
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$/.test(normalized)) return null;
  const [euros = '0', cents = ''] = normalized.replace(/\./g, '').split(',');
  return Number.parseInt(euros, 10) * 100 + Number.parseInt(cents.padEnd(2, '0') || '00', 10);
}

/** "64,5", "64,50", "120" → m² × 100. Max 2 decimal places. */
export function parseSqmToX100(raw: string): number | null {
  // Same grammar as money — German decimal comma, optional thousands dots.
  return parseEurToCents(raw);
}

/** Cents → "950,00" (for prefilling inputs; the € sign lives in the label). */
export function centsToEurInput(cents: number): string {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)},${String(abs % 100).padStart(2, '0')}`;
}

/** ISO "2024-03-01" → "01.03.2024" (display; inputs use type=date). */
export function isoToGermanDate(iso: string): string {
  const [year, month, day] = iso.split('-');
  return `${day}.${month}.${year}`;
}
