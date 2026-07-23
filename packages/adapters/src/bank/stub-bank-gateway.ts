import { cents } from '@lokara/domain';
import type { BankGateway, BankTransaction } from './bank-gateway';

/** Fixture transactions matching the seeded demo renters. */
const FIXTURE_TRANSACTIONS: BankTransaction[] = [
  {
    id: 'tx_stub_001',
    bookingDate: '2025-01-03',
    amount: cents(117000),
    direction: 'CREDIT',
    counterpartName: 'Anna Beispiel',
    counterpartIban: 'DE02120300000000202051',
    purpose: 'Miete + NK Wohnung A Januar 2025',
  },
  {
    id: 'tx_stub_002',
    bookingDate: '2025-01-05',
    amount: cents(83000),
    direction: 'CREDIT',
    counterpartName: 'Bernd Muster',
    counterpartIban: 'DE02500105170137075030',
    purpose: 'Miete Wohnung B 01/2025',
  },
];

/** Dev/test/pitch stub. TODO(provider): swap for the finAPI-backed adapter at M6. */
export class StubBankGateway implements BankGateway {
  listTransactions(
    _bankAccountId: string,
    fromIso: string,
    toIso: string,
  ): Promise<BankTransaction[]> {
    return Promise.resolve(
      FIXTURE_TRANSACTIONS.filter((t) => t.bookingDate >= fromIso && t.bookingDate < toIso),
    );
  }
}
