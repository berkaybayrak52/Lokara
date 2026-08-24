'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { MatchOutcome } from '@/lib/contracts';
import {
  BankTransactionListResponseSchema,
  MatchDecisionResultSchema,
  MatchProposalListResponseSchema,
  PaymentLedgerListResponseSchema,
  ReceivableListResponseSchema,
} from '@/lib/contracts';

/**
 * The five existing payment routes behind React Query (docs/15).
 *
 * The screen reads four of them: the proposals carry only ids, so the bank
 * transaction and the receivable are joined in on the client by
 * `proposal-view.buildRows`. There is no endpoint that resolves `renter_id` to
 * a name, and this file does not invent one.
 */

export function useMatchProposals(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'match-proposals'],
    queryFn: () => api(`/a/${accountId}/match-proposals`, MatchProposalListResponseSchema),
    retry: false,
  });
}

export function useBankTransactions(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'bank-transactions'],
    queryFn: () => api(`/a/${accountId}/bank-transactions`, BankTransactionListResponseSchema),
    retry: false,
  });
}

export function useReceivables(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'receivables'],
    queryFn: () => api(`/a/${accountId}/receivables`, ReceivableListResponseSchema),
    retry: false,
  });
}

export function usePaymentLedger(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'payment-ledger'],
    queryFn: () => api(`/a/${accountId}/payment-ledger`, PaymentLedgerListResponseSchema),
    retry: false,
  });
}

export interface DecisionInput {
  transactionId: string;
  outcome: MatchOutcome;
}

/**
 * The landlord's one and only answer to a Needs-Review proposal.
 *
 * A confirmation settles receivables and writes an immutable ledger entry, so
 * all three lists change at once and all three are invalidated — showing a
 * settled Forderung as still open is exactly the drift this screen exists to
 * remove.
 *
 * A 409 (the proposal needs no decision, or a different decision already
 * exists) also refetches: the server state is the authority and the stale row
 * on screen is what produced the conflict. The German sentence in
 * `ApiError.detail` is the server's; the UI prints it, it does not re-author it.
 */
export function useDecideMatch(accountId: string) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    for (const key of ['match-proposals', 'payment-ledger', 'receivables']) {
      void queryClient.invalidateQueries({ queryKey: ['account', accountId, key] });
    }
  };

  return useMutation({
    mutationFn: ({ transactionId, outcome }: DecisionInput) =>
      api(
        `/a/${accountId}/bank-transactions/${transactionId}/decision`,
        MatchDecisionResultSchema,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ outcome }),
        },
      ),
    onSuccess: invalidate,
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: ['account', accountId, 'match-proposals'] });
    },
  });
}
