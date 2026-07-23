import { describe, expect, it } from 'vitest';
import { placeholderStatementHtml } from './placeholder-statement';
import { renderHtmlToPdf } from './render';

describe('placeholderStatementHtml', () => {
  it('carries the Rechtsstand stamp and the tool-not-advice disclaimer', () => {
    const html = placeholderStatementHtml({
      landlordName: 'Demo <Vermieter>',
      buildingLabel: 'Musterstraße 12',
      periodLabel: '2025',
      rechtsstand: 'Rechtsstand 07/2026',
    });
    expect(html).toContain('Rechtsstand 07/2026');
    expect(html).toContain('keine Rechts- oder Steuerberatung');
    expect(html).toContain('Demo &lt;Vermieter&gt;'); // HTML-escaped
  });
});

describe('renderHtmlToPdf', () => {
  it('renders a non-empty PDF via Chromium', async () => {
    let pdf: Buffer;
    try {
      pdf = await renderHtmlToPdf('<h1>Hallo Lokara</h1>');
    } catch (error) {
      // Chromium not downloaded yet (fresh checkout): skip instead of failing —
      // run `pnpm --filter @lokara/pdf install-browser` to enable this test.
      const message = error instanceof Error ? error.message : String(error);
      if (message.includes("Executable doesn't exist")) {
        console.warn('Skipping PDF render test: Chromium missing (run install-browser).');
        return;
      }
      throw error;
    }
    expect(pdf.length).toBeGreaterThan(1000);
    expect(pdf.subarray(0, 5).toString('latin1')).toBe('%PDF-');
  }, 60_000);
});
