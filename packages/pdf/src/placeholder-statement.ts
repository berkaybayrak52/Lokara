/**
 * M0 placeholder statement template. The real NK + heating/CO₂ statement layout
 * arrives with M3. Colors are the docs/05 design tokens; every legal output
 * carries the Rechtsstand stamp and the "tool, not advice" disclaimer.
 */
export interface PlaceholderStatementData {
  readonly landlordName: string;
  readonly buildingLabel: string;
  readonly periodLabel: string;
  readonly rechtsstand: string;
}

export function placeholderStatementHtml(data: PlaceholderStatementData): string {
  return `<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<style>
  :root {
    --color-ink: #18212a;
    --color-green: #1a6558;
    --color-slate: #5c6a6b;
    --color-mint: #e7efeb;
    --color-paper: #fbfbfa;
  }
  body {
    font-family: 'Manrope', 'Helvetica Neue', Arial, sans-serif;
    color: var(--color-ink);
    background: var(--color-paper);
    margin: 0;
    font-size: 12pt;
  }
  h1 {
    font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
    font-size: 20pt;
    margin: 0 0 4mm;
  }
  .meta { color: var(--color-slate); margin-bottom: 12mm; }
  .band { height: 3mm; background: var(--color-green); margin-bottom: 10mm; }
  .placeholder {
    background: var(--color-mint);
    border-radius: 8px;
    padding: 10mm;
    margin-bottom: 12mm;
  }
  footer {
    color: var(--color-slate);
    font-size: 9pt;
    border-top: 0.5pt solid var(--color-slate);
    padding-top: 4mm;
  }
</style>
</head>
<body>
  <div class="band"></div>
  <h1>Betriebskostenabrechnung</h1>
  <p class="meta">
    ${escapeHtml(data.buildingLabel)} · Abrechnungszeitraum ${escapeHtml(data.periodLabel)}<br />
    Vermieter: ${escapeHtml(data.landlordName)}
  </p>
  <div class="placeholder">
    <strong>Platzhalter (M0):</strong> Die vollständige Nebenkosten- und Heizkostenabrechnung
    wird ab Meilenstein M3 hier gerendert.
  </div>
  <footer>
    ${escapeHtml(data.rechtsstand)} · Erstellt mit Lokara.
    Dieses Dokument wurde rechtskonform erstellt; es stellt keine Rechts- oder Steuerberatung dar.
  </footer>
</body>
</html>`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
