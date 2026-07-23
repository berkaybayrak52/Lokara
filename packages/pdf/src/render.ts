import { chromium } from 'playwright';

export interface PdfOptions {
  /** A4 by default; statements are printed documents. */
  readonly format?: 'A4' | 'Letter';
}

/**
 * Renders an HTML string to a PDF buffer via headless Chromium.
 * Launches one browser per call for now — pooling arrives when volume demands it.
 */
export async function renderHtmlToPdf(html: string, options: PdfOptions = {}): Promise<Buffer> {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle' });
    return await page.pdf({
      format: options.format ?? 'A4',
      printBackground: true,
      margin: { top: '20mm', bottom: '20mm', left: '18mm', right: '18mm' },
    });
  } finally {
    await browser.close();
  }
}
