'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  StatusNote,
} from '@lokara/ui';
import { useEffect, useRef, useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';
import type { PaymentWorkspaceRow } from '@/lib/contracts';

import { LedgerList } from './ledger-list';
import { buildRows } from './proposal-view';
import {
  type PaymentWorkspaceStatus,
  useBankTransactions,
  useBulkClassifyTransactions,
  useClassifyTransaction,
  useDecideMatch,
  useMatchProposals,
  usePaymentLedger,
  usePaymentWorkspace,
  usePaymentWorkspaceAccounts,
  useReceivables,
} from './queries';
import { ReviewList } from './review-list';

const STATUS_FILTERS: Array<{ key: PaymentWorkspaceStatus; label: string }> = [
  { key: 'all', label: 'Alle' },
  { key: 'unassigned', label: 'Nicht zugeordnet' },
  { key: 'review', label: 'Prüfen' },
  { key: 'assigned', label: 'Zugeordnet' },
  { key: 'partial', label: 'Teilweise' },
  { key: 'ignored', label: 'Ignoriert' },
];

function eur(cents: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
}

function germanDate(value: string): string {
  return new Intl.DateTimeFormat('de-DE').format(new Date(`${value}T12:00:00`));
}

function StatusPill({ row }: { row: PaymentWorkspaceRow }) {
  const tone =
    row.status === 'assigned'
      ? 'bg-success/15 text-forest'
      : row.status === 'review' || row.status === 'partial'
        ? 'bg-warning/20 text-ink'
        : row.status === 'ignored'
          ? 'bg-slate/15 text-slate'
          : 'bg-danger/10 text-danger';
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${tone}`}>
      {row.status_label}
    </span>
  );
}

type PaymentAccountContext = {
  display_name: string;
  masked_iban: string;
  consent_status: 'active' | 'expiring' | 'reconnect';
  consent_expires_at: string | null;
};

function consentText(account: PaymentAccountContext): string {
  if (account.consent_status === 'reconnect') return 'Einwilligung abgelaufen';
  if (!account.consent_expires_at) return 'Kein Ablaufdatum dokumentiert';
  const expiry = new Intl.DateTimeFormat('de-DE').format(new Date(account.consent_expires_at));
  return account.consent_status === 'expiring'
    ? `Einwilligung läuft am ${expiry} ab`
    : `Einwilligung bis ${expiry}`;
}

function PaymentDrawer({
  row,
  accountId,
  onClose,
}: {
  row: PaymentWorkspaceRow;
  accountId: string;
  onClose: () => void;
}) {
  const classify = useClassifyTransaction(accountId);
  const decide = useDecideMatch(accountId);
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    const siblings = dialog
      ? Array.from(dialog.parentElement?.children ?? []).filter((node) => node !== dialog)
      : [];
    const priorStates = siblings.map((node) => ({
      node: node as HTMLElement,
      ariaHidden: node.getAttribute('aria-hidden'),
      inert: (node as HTMLElement).inert,
    }));
    for (const sibling of siblings) {
      const element = sibling as HTMLElement;
      element.inert = true;
      element.setAttribute('aria-hidden', 'true');
    }

    const listener = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0]!;
      const last = focusable.at(-1)!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', listener);
    closeRef.current?.focus();
    return () => {
      window.removeEventListener('keydown', listener);
      for (const state of priorStates) {
        state.node.inert = state.inert;
        if (state.ariaHidden === null) state.node.removeAttribute('aria-hidden');
        else state.node.setAttribute('aria-hidden', state.ariaHidden);
      }
    };
  }, [onClose]);

  return (
    <aside
      ref={dialogRef}
      tabIndex={-1}
      aria-label="Buchungsdetails"
      aria-modal="true"
      role="dialog"
      className="fixed inset-y-0 right-0 z-50 w-full max-w-[400px] overflow-y-auto border-l border-mint bg-paper p-6 shadow-xl"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate">Buchungsdetails</p>
          <h2 className="font-display text-2xl font-bold text-ink">
            {row.counterpart_name ?? 'Unbekannte Gegenpartei'}
          </h2>
        </div>
        <button
          ref={closeRef}
          type="button"
          onClick={onClose}
          className="rounded px-2 py-1 text-sm underline focus-visible:outline-2 focus-visible:outline-ring"
        >
          Schließen
        </button>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-slate">Betrag</dt>
          <dd className="font-semibold tabular-nums">{eur(row.amount_cents)}</dd>
        </div>
        <div>
          <dt className="text-slate">Richtung</dt>
          <dd>{row.direction === 'incoming' ? 'Eingang' : 'Ausgang'}</dd>
        </div>
        <div>
          <dt className="text-slate">Buchung</dt>
          <dd>{germanDate(row.booking_date)}</dd>
        </div>
        <div>
          <dt className="text-slate">Wertstellung</dt>
          <dd>{germanDate(row.value_date)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-slate">Konto</dt>
          <dd>{row.account_label}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-slate">Gegenkonto</dt>
          <dd>{row.counterpart_iban_masked ?? 'Nicht übermittelt'}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-slate">Verwendungszweck</dt>
          <dd className="break-words">{row.purpose ?? 'Nicht übermittelt'}</dd>
        </div>
      </dl>

      <div className="mt-6 rounded-lg border border-mint bg-card p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold">Zuordnung</h3>
          <StatusPill row={row} />
        </div>
        <p className="mt-2 text-sm">{row.assignment_label ?? 'Keine Forderung zugeordnet.'}</p>
        {row.open_cents !== null ? (
          <p className="mt-1 text-sm text-slate">Noch offen: {eur(row.open_cents)}</p>
        ) : null}
        {row.status === 'review' && row.receivable_id ? (
          <Button
            className="mt-4"
            disabled={decide.isPending}
            onClick={() => decide.mutate({ transactionId: row.id, outcome: 'confirmed' })}
          >
            Vorschlag bestätigen
          </Button>
        ) : null}
        {row.status === 'unassigned' ? (
          <p className="mt-3 text-xs text-slate">
            Freie manuelle Zuordnung bleibt deaktiviert, bis die Regel für endgültig abgelehnte
            Vorschläge freigegeben ist.
          </p>
        ) : null}
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {row.ignored ? (
          <Button
            variant="outline"
            disabled={classify.isPending}
            onClick={() => classify.mutate({ transactionId: row.id, action: 'restored' })}
          >
            Ignorieren aufheben
          </Button>
        ) : row.available_actions.includes('ignore') ? (
          <Button
            variant="outline"
            disabled={classify.isPending}
            onClick={() =>
              classify.mutate({
                transactionId: row.id,
                action: 'ignored',
                reason: 'Privat / nicht relevant',
              })
            }
          >
            Ignorieren
          </Button>
        ) : null}
      </div>

      <details className="mt-8 rounded-lg border border-mint p-4">
        <summary className="cursor-pointer font-semibold">Warum dieser Vorschlag?</summary>
        <p className="mt-2 text-sm text-slate">
          {row.match_reason_de ?? 'Noch kein Matching-Lauf oder kein belastbarer Vorschlag.'}
        </p>
        {row.confidence !== null ? (
          <p className="mt-2 text-xs text-slate">
            Technische Entscheidungshilfe: {row.confidence}/100. Kein rechtlicher Nachweis.
          </p>
        ) : null}
      </details>

      <section className="mt-8" aria-labelledby="history-title">
        <h3 id="history-title" className="font-semibold">
          Historie
        </h3>
        {row.history.length === 0 ? (
          <p className="mt-2 text-sm text-slate">Noch kein Ereignis.</p>
        ) : (
          <ol className="mt-3 space-y-3">
            {row.history.map((event) => (
              <li
                key={`${event.kind}-${event.created_at}`}
                className="border-l-2 border-mint pl-3 text-sm"
              >
                <p>{event.label}</p>
                <p className="text-xs text-slate">
                  {new Intl.DateTimeFormat('de-DE', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  }).format(new Date(event.created_at))}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </aside>
  );
}

export function ZahlungenPage({ accountId }: { accountId: string }) {
  const [status, setStatus] = useState<PaymentWorkspaceStatus>('all');
  const [bankAccountId, setBankAccountId] = useState('');
  const [direction, setDirection] = useState<'all' | 'incoming' | 'outgoing'>('all');
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [cursor, setCursor] = useState('');
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<PaymentWorkspaceRow | null>(null);
  const rowRefs = useRef(new Map<string, HTMLButtonElement>());
  const accounts = usePaymentWorkspaceAccounts(accountId);
  const bulkClassify = useBulkClassifyTransactions(accountId);
  const workspace = usePaymentWorkspace(accountId, {
    status,
    bankAccountId: bankAccountId || undefined,
    direction,
    search: search || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
    cursor: cursor || undefined,
  });
  const proposals = useMatchProposals(accountId);
  const transactions = useBankTransactions(accountId);
  const receivables = useReceivables(accountId);
  const ledger = usePaymentLedger(accountId);
  const reviewPending = proposals.isPending || transactions.isPending || receivables.isPending;
  const reviewError = proposals.isError || transactions.isError || receivables.isError;
  const reviewRows =
    proposals.data && transactions.data && receivables.data
      ? buildRows({
          proposals: proposals.data.transactions,
          transactions: transactions.data.transactions,
          receivables: receivables.data.receivables,
        })
      : [];

  useEffect(() => {
    setCursor('');
    setCursorHistory([]);
    setSelectedIds(new Set());
  }, [bankAccountId, dateFrom, dateTo, direction, search, status]);

  const selectableRows =
    workspace.data?.rows.filter(
      (row) =>
        row.available_actions.includes('ignore') || row.available_actions.includes('restore'),
    ) ?? [];
  const selectedRows = selectableRows.filter((row) => selectedIds.has(row.id));
  const bulkAction =
    selectedRows.length > 0 &&
    selectedRows.every((row) => row.available_actions.includes('restore'))
      ? 'restored'
      : selectedRows.length > 0 &&
          selectedRows.every((row) => row.available_actions.includes('ignore'))
        ? 'ignored'
        : null;
  const allSelectableSelected =
    selectableRows.length > 0 && selectableRows.every((row) => selectedIds.has(row.id));
  const accountRows = accounts.data?.accounts ?? [];
  const currentAccount = accountRows.find((account) => account.id === bankAccountId);
  const nextConsentAccount = [...accountRows]
    .filter((account) => account.consent_expires_at !== null)
    .sort((left, right) =>
      (left.consent_expires_at ?? '').localeCompare(right.consent_expires_at ?? ''),
    )[0];
  const accountContext = accounts.isPending
    ? 'Mietkonten werden geladen'
    : currentAccount
      ? `${currentAccount.display_name} · ${currentAccount.masked_iban} · ${consentText(currentAccount)}`
      : accountRows.length > 0
        ? `Alle ${accountRows.length} Mietkonten${nextConsentAccount ? ` · Nächster Einwilligungsablauf: ${nextConsentAccount.display_name} am ${new Intl.DateTimeFormat('de-DE').format(new Date(nextConsentAccount.consent_expires_at ?? ''))}` : ''}`
        : 'Keine Mietkonten verfügbar';

  const closeDrawer = () => {
    const id = selected?.id;
    setSelected(null);
    window.setTimeout(() => {
      if (id) rowRefs.current.get(id)?.focus();
    }, 0);
  };

  return (
    <main className="py-10">
      <PageHeader title="Zahlungen" description="Bankumsätze prüfen und Zahlungen zuordnen." />

      <div className="mb-5 flex justify-end">
        <Button
          disabled
          title="Bar- und manuelle Zahlungen benötigen den freigegebenen Nachweisprozess."
        >
          Zahlung erfassen
        </Button>
      </div>

      {accounts.isError ? (
        <StatusNote kind="danger" label="Bankkonten konnten nicht geladen werden.">
          Erneut laden oder später versuchen.
        </StatusNote>
      ) : null}
      {accounts.isSuccess && accounts.data.accounts.length === 0 ? (
        <StatusNote kind="warning" label="Noch kein Bankkonto verbunden.">
          Die produktive Bankverbindung ist noch nicht eingerichtet.
        </StatusNote>
      ) : null}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-2" aria-label="Zahlungsstatus">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.key}
                type="button"
                onClick={() => setStatus(filter.key)}
                aria-pressed={status === filter.key}
                className={`rounded-full px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-ring ${status === filter.key ? 'bg-forest text-paper' : 'bg-mint text-ink'}`}
              >
                {filter.label} · {workspace.data?.counts[filter.key] ?? 0}
              </button>
            ))}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <label className="text-sm font-medium">
              Suche
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Gegenpartei oder Zweck"
                className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
              />
            </label>
            <label className="text-sm font-medium">
              Konto
              <select
                value={bankAccountId}
                onChange={(event) => setBankAccountId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
              >
                <option value="">Alle Mietkonten</option>
                {accounts.data?.accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium">
              Richtung
              <select
                value={direction}
                onChange={(event) =>
                  setDirection(event.target.value as 'all' | 'incoming' | 'outgoing')
                }
                className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
              >
                <option value="all">Alle</option>
                <option value="incoming">Eingänge</option>
                <option value="outgoing">Ausgänge</option>
              </select>
            </label>
            <label className="text-sm font-medium">
              Von
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
                className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
              />
            </label>
            <label className="text-sm font-medium">
              Bis
              <input
                type="date"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
                className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
              />
            </label>
          </div>
          <p className="mt-4 border-t border-mint pt-3 text-sm text-slate">
            <span className="font-semibold text-ink">Aktuell:</span> {accountContext}
          </p>
        </CardContent>
      </Card>

      <section className="mt-5" aria-label="Umsatzliste" aria-busy={workspace.isPending}>
        {selectedRows.length > 0 ? (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-mint px-4 py-3">
            <p className="text-sm font-semibold">{selectedRows.length} ausgewählt</p>
            <Button
              variant="outline"
              disabled={bulkAction === null || bulkClassify.isPending}
              onClick={() => {
                if (bulkAction === null) return;
                bulkClassify.mutate(
                  {
                    transactionIds: selectedRows.map((row) => row.id),
                    action: bulkAction,
                    reason: bulkAction === 'ignored' ? 'Sammelaktion' : undefined,
                  },
                  {
                    onSuccess: (result) => {
                      setSelectedIds(
                        new Set(
                          result.results
                            .filter((item) => !item.ok)
                            .map((item) => item.transaction_id),
                        ),
                      );
                    },
                  },
                );
              }}
            >
              {bulkAction === 'restored' ? 'Ignorieren aufheben' : 'Auswahl ignorieren'}
            </Button>
          </div>
        ) : null}
        {workspace.isPending ? (
          <div
            role="status"
            className="h-72 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
          >
            <span className="sr-only">Umsätze werden geladen.</span>
          </div>
        ) : workspace.isError ? (
          <StatusNote kind="danger" label="Umsätze konnten nicht geladen werden.">
            Die bisherige Auswahl bleibt erhalten. Versuchen Sie es erneut.
          </StatusNote>
        ) : workspace.data.rows.length === 0 ? (
          <StatusNote kind="warning" label="Keine Umsätze für diese Filter.">
            Passen Sie Suche, Konto oder Status an.
          </StatusNote>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-mint bg-card">
            <table className="w-full min-w-[1050px] border-collapse text-sm">
              <thead className="bg-mint/70 text-left">
                <tr>
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={allSelectableSelected}
                      disabled={selectableRows.length === 0}
                      onChange={(event) =>
                        setSelectedIds(
                          event.target.checked
                            ? new Set(selectableRows.map((row) => row.id))
                            : new Set(),
                        )
                      }
                      aria-label="Alle bearbeitbaren Umsätze dieser Seite auswählen"
                    />
                  </th>
                  <th className="px-4 py-3">Buchung</th>
                  <th className="px-4 py-3">Gegenpartei</th>
                  <th className="px-4 py-3">Konto</th>
                  <th className="px-4 py-3">Zuordnung</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Betrag</th>
                  <th className="px-4 py-3">
                    <span className="sr-only">Aktion</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {workspace.data.rows.map((row) => {
                  const selectable =
                    row.available_actions.includes('ignore') ||
                    row.available_actions.includes('restore');
                  return (
                    <tr key={row.id} className="border-t border-mint hover:bg-mint/30">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(row.id)}
                          disabled={!selectable}
                          onChange={(event) =>
                            setSelectedIds((current) => {
                              const next = new Set(current);
                              if (event.target.checked) next.add(row.id);
                              else next.delete(row.id);
                              return next;
                            })
                          }
                          aria-label={`Umsatz von ${row.counterpart_name ?? 'Unbekannt'} auswählen`}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium">{germanDate(row.booking_date)}</p>
                        <p className="max-w-52 truncate text-xs text-slate">
                          {row.purpose ?? 'Kein Verwendungszweck'}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <p>{row.counterpart_name ?? 'Unbekannt'}</p>
                      </td>
                      <td className="px-4 py-3 font-medium">{row.account_label}</td>
                      <td className="px-4 py-3">{row.assignment_label ?? 'Nicht zugeordnet'}</td>
                      <td className="px-4 py-3">
                        <StatusPill row={row} />
                      </td>
                      <td className="px-4 py-3 text-right font-semibold tabular-nums">
                        {eur(row.amount_cents)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          ref={(node) => {
                            if (node) rowRefs.current.set(row.id, node);
                          }}
                          type="button"
                          onClick={() => setSelected(row)}
                          className="rounded px-2 py-1 font-semibold text-forest underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-ring"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {workspace.data && (cursorHistory.length > 0 || workspace.data.next_cursor) ? (
        <nav className="mt-4 flex items-center justify-between gap-3" aria-label="Umsatzseiten">
          <Button
            variant="outline"
            disabled={cursorHistory.length === 0 || workspace.isFetching}
            onClick={() => {
              const previous = cursorHistory.at(-1) ?? '';
              setCursorHistory((items) => items.slice(0, -1));
              setSelectedIds(new Set());
              setCursor(previous);
            }}
          >
            Zurück
          </Button>
          <p className="text-sm text-slate">{workspace.data.total} Umsätze im gewählten Status</p>
          <Button
            variant="outline"
            disabled={!workspace.data.next_cursor || workspace.isFetching}
            onClick={() => {
              setCursorHistory((items) => [...items, cursor]);
              setSelectedIds(new Set());
              setCursor(workspace.data.next_cursor ?? '');
            }}
          >
            Weitere
          </Button>
        </nav>
      ) : null}

      <div className="mt-8 space-y-8">
        <section aria-labelledby="zuordnung-titel" className="space-y-4">
          <div>
            <h2 id="zuordnung-titel" className="font-display text-2xl font-bold">
              Zuordnung prüfen
            </h2>
            <p className="mt-1 max-w-prose text-slate">
              Offene Prüfungen zuerst, darunter die bereits entschiedenen Umsätze als Nachweis.
            </p>
          </div>

          <StatusNote kind="warning" label="Bewertung ist eine Entscheidungshilfe.">
            Die Punktgewichte der Zuordnungsprüfung sind eine Lokara-Konvention (
            <span className="whitespace-nowrap">Rechtsstand 07/2026</span>) und noch nicht rechtlich
            geprüft. Sie zeigen, wie sicher ein Vorschlag technisch ist — sie sind kein rechtlicher
            Nachweis dafür, dass eine Zahlung zu einer Forderung gehört. Die Entscheidung treffen
            Sie.
          </StatusNote>

          {reviewPending ? (
            <div
              role="status"
              aria-busy="true"
              className="h-64 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            >
              <span className="sr-only">Zahlungen werden geladen …</span>
            </div>
          ) : reviewError ? (
            <StatusNote kind="danger" label="Zahlungen konnten nicht geladen werden.">
              Laden Sie die Seite neu oder versuchen Sie es später erneut.
            </StatusNote>
          ) : reviewRows.length === 0 ? (
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
            <ReviewList accountId={accountId} rows={reviewRows} />
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
            <LedgerList
              entries={ledger.data.entries}
              receivables={receivables.data?.receivables ?? []}
            />
          )}
        </section>

        <p className="max-w-prose text-sm text-slate">
          Die Verrechnung folgt §§ 366, 367 BGB. Lokara unterstützt Vermieter bei der
          rechtskonformen Verwaltung ihrer Objekte und ersetzt keine Rechts- oder Steuerberatung.
        </p>
      </div>
      {selected ? (
        <PaymentDrawer row={selected} accountId={accountId} onClose={closeDrawer} />
      ) : null}
    </main>
  );
}
