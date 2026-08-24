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

/**
 * Cents → "1.234,56 €" for DISPLAY (German grouping, decimal comma, € sign).
 *
 * Distinct from `centsToEurInput`, which stays ungrouped and signless because a
 * `<input>` value has to round-trip back through `parseEurToCents`. Negatives
 * are real here: a Stornobuchung in the Zahlungsjournal carries negative cents.
 *
 * Integer arithmetic only — the euros and the cents are split before anything
 * is rendered, so no float ever holds a money value.
 */
export function centsToEurDisplay(cents: number): string {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const euros = Math.floor(abs / 100)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${sign}${euros},${String(abs % 100).padStart(2, '0')} €`;
}

/**
 * "1.800", "241,5", "168500,25" → register value × 1000. Max 3 decimals.
 *
 * Meter registers are not money: a water meter reads to the litre (3 decimals)
 * and a heat meter to whole kWh. Same fixed-point discipline though — the
 * value crosses the wire as an integer, so no float ever reaches a consumption
 * that turns into money.
 */
export function parseMeterValueToX1000(raw: string): number | null {
  const normalized = raw.trim().replace(/\s/g, '');
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,3})?$|^\d+(,\d{1,3})?$/.test(normalized)) return null;
  const [whole = '0', fraction = ''] = normalized.replace(/\./g, '').split(',');
  return Number.parseInt(whole, 10) * 1000 + Number.parseInt(fraction.padEnd(3, '0') || '000', 10);
}

/** Register value × 1000 → "241,5" / "1.800" (German, trailing zeros dropped). */
export function meterValueToDisplay(valueX1000: number): string {
  const whole = Math.floor(valueX1000 / 1000);
  const fraction = String(valueX1000 % 1000)
    .padStart(3, '0')
    .replace(/0+$/, '');
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return fraction ? `${grouped},${fraction}` : grouped;
}

/** ISO "2024-03-01" → "01.03.2024" (display; inputs use type=date). */
export function isoToGermanDate(iso: string): string {
  const [year, month, day] = iso.split('-');
  return `${day}.${month}.${year}`;
}
