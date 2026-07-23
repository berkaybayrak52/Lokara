import { describe, expect, it } from 'vitest';
import { StubBankGateway } from './bank/stub-bank-gateway';
import { StubEmailGateway } from './email/stub-email-gateway';
import { StubVisionGateway } from './vision/stub-vision-gateway';

describe('StubBankGateway', () => {
  it('returns fixture transactions filtered by date window', async () => {
    const gw = new StubBankGateway();
    const all = await gw.listTransactions('any', '2025-01-01', '2025-02-01');
    expect(all).toHaveLength(2);
    const none = await gw.listTransactions('any', '2025-02-01', '2025-03-01');
    expect(none).toHaveLength(0);
  });
});

describe('StubVisionGateway', () => {
  it('extracts the canned sample invoice with integer-cents amount', async () => {
    const gw = new StubVisionGateway();
    const fields = await gw.extractInvoice({ fileName: 'rechnung.pdf', bytes: new Uint8Array() });
    expect(fields.totalAmount).toBe(120000);
    expect(fields.costCategory).toBe('Müllabfuhr');
    expect(fields.confidence).toBeGreaterThan(0.9);
  });
});

describe('StubEmailGateway', () => {
  it('records sends in memory with a receipt', async () => {
    const gw = new StubEmailGateway();
    const receipt = await gw.send({
      to: 'mieter@example.de',
      fromName: 'Demo Vermieter',
      subject: 'Ihre Nebenkostenabrechnung 2025',
      htmlBody: '<p>Guten Tag</p>',
    });
    expect(receipt.status).toBe('QUEUED');
    expect(gw.sent).toHaveLength(1);
  });
});
