import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { placeholderStatementHtml } from './placeholder-statement';
import { renderHtmlToPdf } from './render';

async function main(): Promise<void> {
  const html = placeholderStatementHtml({
    landlordName: 'Demo Vermieter',
    buildingLabel: 'Musterstraße 12, 60311 Frankfurt am Main',
    periodLabel: '01.01.2025 – 31.12.2025',
    rechtsstand: 'Rechtsstand 07/2026',
  });
  const pdf = await renderHtmlToPdf(html);
  const outDir = path.join(__dirname, '..', 'output');
  await mkdir(outDir, { recursive: true });
  const outFile = path.join(outDir, 'placeholder-statement.pdf');
  await writeFile(outFile, pdf);
  console.log(`PDF written: ${outFile} (${pdf.length} bytes)`);
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
