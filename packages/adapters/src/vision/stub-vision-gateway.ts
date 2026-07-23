import { cents } from '@lokara/domain';
import type { ExtractedInvoiceFields, VisionGateway } from './vision-gateway';

/**
 * Canned-demo stub (M4 pitch flow): every upload "extracts" the sample garbage
 * invoice from the demo scenario. TODO(provider): EU+AVV vision provider.
 */
export class StubVisionGateway implements VisionGateway {
  extractInvoice(_document: {
    fileName: string;
    bytes: Uint8Array;
  }): Promise<ExtractedInvoiceFields> {
    return Promise.resolve({
      vendorName: 'Stadtreinigung Frankfurt GmbH',
      invoiceDate: '2025-12-15',
      totalAmount: cents(120000),
      costCategory: 'Müllabfuhr',
      confidence: 0.97,
    });
  }
}
