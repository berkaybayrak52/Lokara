import type { Cents } from '@lokara/domain';

/**
 * Port for document extraction (Beleg-OCR + migration import, one pipeline — M4).
 * TODO(provider): real implementation must offer EU processing + AVV and is a
 * listed sub-processor. Chosen before real customer documents flow; never hardcoded.
 */
export interface ExtractedInvoiceFields {
  readonly vendorName: string;
  readonly invoiceDate: string;
  readonly totalAmount: Cents;
  readonly costCategory: string;
  /** 0..1 — the review UI shows low-confidence fields for correction. */
  readonly confidence: number;
}

export interface VisionGateway {
  extractInvoice(document: {
    fileName: string;
    bytes: Uint8Array;
  }): Promise<ExtractedInvoiceFields>;
}
