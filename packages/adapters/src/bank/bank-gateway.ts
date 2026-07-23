import type { Cents } from '@lokara/domain';

/**
 * Port for PSD2 account-information access (AIS).
 * TODO(provider): real implementation consumes a licensed AISP (finAPI/Tink,
 * EU + AVV, sub-processor) at M6. Never build the licence ourselves.
 */
export interface BankTransaction {
  readonly id: string;
  /** Booking date, ISO date — the tax-relevant payment date (§11 EStG). */
  readonly bookingDate: string;
  readonly amount: Cents;
  readonly direction: 'CREDIT' | 'DEBIT';
  readonly counterpartName: string;
  readonly counterpartIban: string;
  readonly purpose: string;
}

export interface BankGateway {
  /** Lists transactions for a connected bank account within [fromIso, toIso). */
  listTransactions(bankAccountId: string, fromIso: string, toIso: string): Promise<BankTransaction[]>;
}
