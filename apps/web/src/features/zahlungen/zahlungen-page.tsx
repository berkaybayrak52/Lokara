'use client';

import { Card, CardDescription, CardHeader, CardTitle, StatusNote } from '@lokara/ui';

import { PageHeader } from '@/features/portal/page-header';

import { LedgerList } from './ledger-list';
import { buildRows } from './proposal-view';
import { ReviewList } from './review-list';
import {
  useBankTransactions,
  useMatchProposals,
  usePaymentLedger,
  useReceivables,
} from './queries';

/**
 * Zahlungen (docs/15) — the landlord's payment screen.
 *
 * Two halves that must not be confused. Above: what the matching run proposed
 * and what still needs a human answer. Below: the Zahlungsjournal, the
 * immutable record of what was actually booked.
 *
 * The screen never assigns a payment by hand. It answers the server's proposal
 * with confirmed / rejected / duplicate; which receivable a confirmed amount
 * settles is decided by §§ 366, 367 BGB on the server, not by a picker here.
 */
export function ZahlungenPage({ accountId }: { accountId: string }) {
  const proposals = useMatchProposals(accountId);
  const transactions = useBankTransactions(accountId);
  const receivables = useReceivables(accountId);
  const ledger = usePaymentLedger(accountId);

  const isPending = proposals.isPending || transactions.isPending || receivables.isPending;
  const isError = proposals.isError || transactions.isError || receivables.isError;

  const rows =
    proposals.data && transactions.data && receivables.data
      ? buildRows({
          proposals: proposals.data.transactions,
          transactions: transactions.data.transactions,
          receivables: receivables.data.receivables,
        })
      : [];

  return (
    <main className="py-10">
      <PageHeader
        title="Zahlungen"
        description="Bankumsätze und die dazu vorgeschlagenen Forderungen. Eindeutige Treffer werden automatisch gebucht; alles andere legen wir Ihnen zur Prüfung vor. Eine getroffene Entscheidung bleibt bestehen und wird nicht überschrieben."
      />

      <div className="space-y-8">
        <section aria-labelledby="zuordnung-titel" className="space-y-4">
          <div>
            <h2 id="zuordnung-titel" className="font-display text-2xl font-bold">
              Zuordnung prüfen
            </h2>
            <p className="mt-1 max-w-prose text-slate">
              Offene Prüfungen zuerst, darunter die bereits entschiedenen Umsätze als Nachweis.
            </p>
          </div>

          {/* The Rechtsstand is written out because CLAUDE.md § 6 requires every
              legal output to carry one — but it is a page-level constant, not
              the value that actually governed this proposal. The authoritative
              per-proposal value is `match_proposal.convention_version`
              (`matching-engine/decision.py`, persisted by `matching_service.py`);
              neither `_candidate_json` nor `list_proposals` returns it, so the
              screen cannot derive it yet. Closing that payload gap belongs to
              M6-C3a, not to this slice. */}
          <StatusNote kind="warning" label="Bewertung ist eine Entscheidungshilfe.">
            Die Punktgewichte der Zuordnungsprüfung sind eine Lokara-Konvention (
            <span className="whitespace-nowrap">Rechtsstand 07/2026</span>) und noch nicht rechtlich
            geprüft. Sie zeigen, wie sicher ein Vorschlag technisch ist — sie sind kein rechtlicher
            Nachweis dafür, dass eine Zahlung zu einer Forderung gehört. Die Entscheidung treffen
            Sie.
          </StatusNote>

          {isPending ? (
            <div
              role="status"
              aria-busy="true"
              className="h-64 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            >
              <span className="sr-only">Zahlungen werden geladen …</span>
            </div>
          ) : isError ? (
            <StatusNote kind="danger" label="Zahlungen konnten nicht geladen werden.">
              Laden Sie die Seite neu oder versuchen Sie es später erneut.
            </StatusNote>
          ) : rows.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Zuordnungsvorschläge</CardTitle>
                <CardDescription>
                  Es wurde noch kein Abgleich zwischen Bankumsätzen und Forderungen ausgeführt.
                  Deshalb ist diese Liste leer — das bedeutet nicht, dass alle Zahlungen bereits
                  zugeordnet sind. Sobald ein Abgleich gelaufen ist, erscheinen die Vorschläge hier.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <ReviewList accountId={accountId} rows={rows} />
          )}
        </section>

        <section aria-label="Zahlungsjournal" className="space-y-4">
          <div>
            <h2 className="font-display text-2xl font-bold">Zahlungsjournal</h2>
            <p className="mt-1 max-w-prose text-slate">
              Alle gebuchten Zahlungen und Stornos, neueste zuerst. Die Einträge sind unveränderlich
              und dienen als Nachweis; sie lassen sich hier weder bearbeiten noch löschen. „Erfasst
              am“ nennt den Zeitpunkt der Buchung in Lokara, nicht das Buchungs- oder
              Wertstellungsdatum der Bank.
            </p>
          </div>

          {ledger.isPending ? (
            <div
              role="status"
              aria-busy="true"
              className="h-40 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            >
              <span className="sr-only">Zahlungsjournal wird geladen …</span>
            </div>
          ) : ledger.isError ? (
            <StatusNote kind="danger" label="Zahlungsjournal konnte nicht geladen werden.">
              Bitte erneut versuchen.
            </StatusNote>
          ) : ledger.data.entries.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Buchung</CardTitle>
                <CardDescription>
                  Es wurde bisher keine Zahlung verbucht. Ein Eintrag entsteht erst, wenn ein Umsatz
                  automatisch zugeordnet oder von Ihnen bestätigt wurde.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            // The journal names the settled Forderung by joining the
            // allocation's `receivable_id` against the receivable list. If that
            // list is still loading or failed the entry stays complete and the
            // Forderung line says so, rather than inventing a label.
            <LedgerList
              entries={ledger.data.entries}
              receivables={receivables.data?.receivables ?? []}
            />
          )}
        </section>

        {/* One approved web spelling, identical to the styleguide footer. It
            must never be reworded into an attestation that the work on this
            page was carried out in conformity with the law. */}
        <p className="max-w-prose text-sm text-slate">
          Die Verrechnung folgt §§ 366, 367 BGB. Lokara unterstützt Vermieter bei der
          rechtskonformen Verwaltung ihrer Objekte und ersetzt keine Rechts- oder Steuerberatung.
        </p>
      </div>
    </main>
  );
}
