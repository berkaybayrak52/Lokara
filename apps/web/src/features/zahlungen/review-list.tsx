'use client';

import { Button, Card, CardContent, CardHeader, CardTitle, StatusNote } from '@lokara/ui';
import { useEffect, useRef, useState } from 'react';

import { ApiError } from '@/lib/api';
import type { MatchOutcome } from '@/lib/contracts';
import { centsToEurDisplay, isoToGermanDate } from '@/lib/format';

import {
  groupOf,
  isDecidable,
  periodToGerman,
  type CandidateRow,
  type ProposalRow,
  type ReviewGroup,
  type SignalPart,
} from './proposal-view';
import { useDecideMatch } from './queries';

/**
 * The review list (docs/15 § 4).
 *
 * Four sections, in the order the landlord needs them: open work first, then
 * the evidence. Only an open Needs-Review row carries buttons — everything
 * else has already been decided by the engine or by a person, and a decision is
 * final and immutable.
 *
 * A renter is never named here. The proposals carry `renter_id` only, no route
 * resolves it to a legal name, and printing a bare id where a name belongs
 * would read as one. The payer is identified the way the bank identified them:
 * counterpart plus purpose, against the Forderung the candidate points at.
 */

const SECTIONS: { group: ReviewGroup; title: string; description: string }[] = [
  {
    group: 'needs_review',
    title: 'Offene Prüfungen',
    description:
      'Diese Zahlungen konnten nicht eindeutig zugeordnet werden. Ihre Entscheidung ist endgültig und wird nicht überschrieben.',
  },
  {
    group: 'auto_booked',
    title: 'Automatisch gebucht',
    description: 'Eindeutig zugeordnet und bereits im Zahlungsjournal verbucht. Nur zur Ansicht.',
  },
  {
    group: 'decided',
    title: 'Bereits entschieden',
    description: 'Von Ihnen entschieden. Die Entscheidung bleibt als Nachweis erhalten.',
  },
  {
    group: 'no_action',
    title: 'Ohne Zuordnung',
    description:
      'Keine Forderung erreicht die Prüfschwelle, oder der Umsatz wurde als Dublette erkannt. Es wurde nichts gebucht.',
  },
];

const DECISION_LABELS: Record<string, string> = {
  auto_match: 'Automatisch zugeordnet',
  needs_review: 'Prüfung nötig',
  unmatched: 'Keine Zuordnung',
  deduped: 'Als Dublette erkannt',
};

const OUTCOME_LABELS: Record<MatchOutcome, string> = {
  confirmed: 'Bestätigt',
  rejected: 'Abgelehnt',
  duplicate: 'Als Dublette markiert',
};

/**
 * The label depends on the points, because two different docs/15 § 4 rows share
 * one signal field: an IBAN unique to one renter scores 60 and can auto-match,
 * an IBAN shared by more than one renter scores 20 and never auto-matches
 * (§ 4, decision rule 4). The same field carries code (15) and surname (10),
 * which are mutually exclusive. One label for both cases would hide exactly the
 * distinction the decision turns on.
 */
function signalLabel(part: SignalPart): string {
  switch (part.key) {
    case 'iban':
      if (!part.met) return 'Keine bekannte IBAN';
      return part.points >= 60
        ? 'IBAN eindeutig einem Mieter zugeordnet'
        : 'IBAN mehreren Mietern bekannt';
    case 'amount':
      return part.met ? 'Betrag stimmt exakt' : 'Betrag stimmt nicht exakt';
    case 'code_or_surname':
      if (!part.met) return 'Kein Zahlungscode und kein Nachname im Verwendungszweck';
      return part.points >= 15
        ? 'Zahlungscode im Verwendungszweck'
        : 'Nachname im Verwendungszweck';
    case 'end_to_end':
      return 'End-to-End-Referenz';
    case 'period':
      return part.met ? 'Zeitraum im Verwendungszweck' : 'Kein Zeitraum im Verwendungszweck';
  }
}

/**
 * The E2E signal is inert, not failed (docs/15 § 4: "15 — inert, see below").
 * The reference it scores against is named in the table and defined nowhere in
 * § 3, so the engine returns 0 for every candidate. Rendering that 0 like an
 * unmet criterion would read as "the E2E reference did not match" — a false
 * negative on a screen whose whole purpose is evidence. It is therefore shown
 * as not yet evaluated, with its own glyph and surface, until M6-C2 adds the
 * real field and makes the signal live.
 */
function isPendingSignal(part: SignalPart): boolean {
  return part.key === 'end_to_end';
}

const CATEGORY_LABELS: Record<string, string> = {
  rent: 'Miete',
  nk_nachzahlung: 'Nachzahlung Betriebskosten',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'offen',
  partial: 'teilweise ausgeglichen',
  settled: 'ausgeglichen',
};

function labelOf(map: Record<string, string>, value: string): string {
  return map[value.toLowerCase()] ?? value;
}

/** Filled 16px glyphs — distinct shapes, so met/unmet never rests on colour. */
function CheckGlyph() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="M8.2 14.3 4 10.1l1.4-1.4 2.8 2.8 6.4-6.4L16 6.5l-7.8 7.8Z" />
    </svg>
  );
}

function DashGlyph() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="M4.5 9h11v2h-11V9Z" />
    </svg>
  );
}

/** Not evaluated — deliberately neither a tick nor a dash (see isPendingSignal). */
function PendingGlyph() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm0 2a6 6 0 1 1 0 12 6 6 0 0 1 0-12Zm-3 5h6v2H7V9Z" />
    </svg>
  );
}

function AlertGlyph() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="M10 2 1.5 17h17L10 2Zm-1 5h2v5H9V7Zm0 6.5h2v2H9v-2Z" />
    </svg>
  );
}

function InfoGlyph() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm-1 4h2v2H9V6Zm0 3.5h2V15H9V9.5Z" />
    </svg>
  );
}

function ChevronGlyph() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="m5.7 7.3 4.3 4.3 4.3-4.3 1.4 1.4-5.7 5.7-5.7-5.7 1.4-1.4Z" />
    </svg>
  );
}

interface DecisionEcho {
  transactionId: string;
  outcome: MatchOutcome;
  counterpart: string;
}

export function ReviewList({ accountId, rows }: { accountId: string; rows: ProposalRow[] }) {
  /**
   * A successful decision moves its card from "Offene Prüfungen" into "Bereits
   * entschieden": the card unmounts, its buttons disappear and focus would fall
   * to <body>, dropping a keyboard user back at the top of the page (WCAG 2.1
   * 2.4.3) with nothing announced (4.1.3). The outcome is therefore held here,
   * one level above the sections, so it can be announced politely and so the
   * remounted card can take focus back.
   */
  const [echo, setEcho] = useState<DecisionEcho | null>(null);

  return (
    <div className="flex flex-col gap-8">
      <p role="status" aria-live="polite" className="sr-only">
        {echo === null
          ? ''
          : `Zahlung von ${echo.counterpart}: ${OUTCOME_LABELS[echo.outcome]}. Der Umsatz steht jetzt unter „Bereits entschieden“.`}
      </p>

      {SECTIONS.map((section) => {
        const inSection = rows.filter((row) => groupOf(row) === section.group);
        if (inSection.length === 0) return null;
        return (
          <section key={section.group} aria-label={section.title}>
            <h3 className="font-display text-lg font-semibold">
              {section.title} ({inSection.length})
            </h3>
            <p className="mt-1 mb-4 max-w-prose text-sm text-slate">{section.description}</p>
            <div className="flex flex-col gap-4">
              {inSection.map((row) => (
                <ProposalCard
                  key={row.transaction_id}
                  accountId={accountId}
                  row={row}
                  takeFocus={echo?.transactionId === row.transaction_id}
                  onDecided={setEcho}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function ProposalCard({
  accountId,
  row,
  takeFocus,
  onDecided,
}: {
  accountId: string;
  row: ProposalRow;
  takeFocus: boolean;
  onDecided: (echo: DecisionEcho) => void;
}) {
  const decidable = isDecidable(row);
  const [detailsOpen, setDetailsOpen] = useState(decidable);
  const decide = useDecideMatch(accountId);
  const detailsId = `kandidaten-${row.transaction_id}`;
  const cardRef = useRef<HTMLDivElement>(null);

  const counterpart = row.transaction?.counterpart_name ?? 'Absender nicht übermittelt';
  const purpose = row.transaction?.purpose ?? 'Kein Verwendungszweck übermittelt';

  // Runs on the remount in the new section too, so focus lands back on the very
  // card the landlord just answered instead of on <body>.
  useEffect(() => {
    if (takeFocus) cardRef.current?.focus();
  }, [takeFocus]);

  const submit = (outcome: MatchOutcome) => {
    decide.mutate(
      { transactionId: row.transaction_id, outcome },
      { onSuccess: () => onDecided({ transactionId: row.transaction_id, outcome, counterpart }) },
    );
  };

  return (
    // tabIndex -1 + focus (not focus-visible): the focus here is programmatic,
    // and a keyboard user must still see where they landed.
    <div
      ref={cardRef}
      tabIndex={-1}
      role="group"
      aria-label={`Zahlung von ${counterpart}`}
      className="rounded-xl focus:outline-2 focus:outline-offset-2 focus:outline-ring"
    >
      <Card>
        <CardHeader className="gap-3 pb-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <CardTitle className="text-base">{counterpart}</CardTitle>
              <p className="mt-1 text-sm break-words text-slate">Verwendungszweck: {purpose}</p>
            </div>
            <div className="text-right">
              <p className="font-display text-xl font-semibold tabular-nums">
                {row.transaction ? centsToEurDisplay(row.transaction.amount_cents) : '—'}
              </p>
              <p className="text-sm text-slate tabular-nums">
                {row.transaction
                  ? `Buchung ${isoToGermanDate(row.transaction.bank_booking_date)}`
                  : 'Umsatz nicht in dieser Liste'}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StateChip label={labelOf(DECISION_LABELS, row.decision)} />
            {row.transaction?.is_potential_duplicate ? (
              <StateChip label="Mögliche Dublette" tone="warning" />
            ) : null}
            {row.confirmation ? (
              <StateChip
                label={`${OUTCOME_LABELS[row.confirmation.outcome]} am ${isoToGermanDate(
                  row.confirmation.confirmed_at.slice(0, 10),
                )}`}
                tone="success"
              />
            ) : null}
          </div>
        </CardHeader>

        <CardContent className="flex flex-col gap-4">
          {/* Verbatim from the server. The client does not re-author or translate
            the reason a decision came out the way it did. */}
          {row.reason_de ? (
            <p className="rounded-lg bg-mint px-4 py-3 text-sm text-ink">
              <span className="font-semibold">Begründung: </span>
              {row.reason_de}
            </p>
          ) : (
            <p className="text-sm text-slate">Für diesen Umsatz liegt keine Begründung vor.</p>
          )}

          {row.candidates.length > 0 ? (
            <div>
              <Button
                variant="ghost"
                size="sm"
                className="-ml-3"
                aria-expanded={detailsOpen}
                aria-controls={detailsId}
                onClick={() => setDetailsOpen((open) => !open)}
              >
                <span
                  className={
                    'transition-transform duration-200 ease-out motion-reduce:transition-none ' +
                    (detailsOpen ? 'rotate-180' : 'rotate-0')
                  }
                >
                  <ChevronGlyph />
                </span>
                {detailsOpen ? 'Bewertung ausblenden' : 'Bewertung anzeigen'}
              </Button>
              <div id={detailsId} hidden={!detailsOpen}>
                {detailsOpen ? (
                  <ul className="mt-3 flex flex-col gap-4">
                    {row.candidates.map((candidate) => (
                      <li key={candidate.proposal_id}>
                        <CandidateBlock candidate={candidate} />
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </div>
          ) : null}

          {decidable ? (
            <div
              className="flex flex-wrap items-center gap-2 border-t border-mint pt-4"
              role="group"
              aria-label={`Entscheidung für die Zahlung von ${counterpart}`}
            >
              <Button size="sm" disabled={decide.isPending} onClick={() => submit('confirmed')}>
                Bestätigen
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={decide.isPending}
                onClick={() => submit('rejected')}
              >
                Ablehnen
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={decide.isPending}
                onClick={() => submit('duplicate')}
              >
                Als Dublette markieren
              </Button>
              <span className="text-xs text-slate">
                {decide.isPending ? 'Wird gespeichert …' : 'Die Entscheidung ist endgültig.'}
              </span>
            </div>
          ) : null}

          {decide.isError ? (
            <StatusNote kind="danger" label="Entscheidung nicht möglich.">
              {/* The server's German sentence, verbatim — it knows why. */}
              {decide.error instanceof ApiError && decide.error.detail
                ? decide.error.detail
                : 'Bitte laden Sie die Seite neu und versuchen Sie es erneut.'}
            </StatusNote>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function CandidateBlock({ candidate }: { candidate: CandidateRow }) {
  const receivable = candidate.receivable;
  // Confidence is min(100, sum) on the server, so the printed weights can add
  // up past the printed total. Say so where the cap actually bites, otherwise a
  // landlord adding the chips up concludes the arithmetic is broken.
  const rawTotal = candidate.signalParts.reduce((sum, part) => sum + part.points, 0);

  return (
    <div className="rounded-lg border border-mint p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold">
          {receivable
            ? `Vorschlag ${candidate.rank}: ${labelOf(CATEGORY_LABELS, receivable.category)} ${periodToGerman(receivable.period)}`
            : `Vorschlag ${candidate.rank}: keine passende Forderung`}
        </p>
        <p className="text-sm text-slate tabular-nums">{candidate.confidence} von 100 Punkten</p>
      </div>

      {receivable ? (
        <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="text-slate">Fällig am</dt>
            <dd className="font-semibold tabular-nums">{isoToGermanDate(receivable.due_date)}</dd>
          </div>
          <div>
            <dt className="text-slate">Offener Betrag</dt>
            <dd className="font-semibold tabular-nums">
              {centsToEurDisplay(receivable.open_cents)}
            </dd>
          </div>
          <div>
            <dt className="text-slate">Forderungsbetrag</dt>
            <dd className="font-semibold tabular-nums">
              {centsToEurDisplay(receivable.expected_cents)}
            </dd>
          </div>
          <div>
            <dt className="text-slate">Status</dt>
            <dd className="font-semibold">{labelOf(STATUS_LABELS, receivable.status)}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-3 text-sm text-slate">
          {candidate.receivable_id === null
            ? 'Die Prüfung hat keine Forderung gefunden, die zu diesem Umsatz passt.'
            : 'Die zugehörige Forderung ist in dieser Liste nicht enthalten.'}
        </p>
      )}

      <ul className="mt-4 flex flex-wrap gap-2">
        {candidate.signalParts.map((part) => {
          const pending = isPendingSignal(part);
          return (
            <li key={part.key}>
              <span
                className={
                  'inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium ' +
                  // Forest Deep on Mint (10,01:1), not Green on Mint: docs/05
                  // § 2.1 keeps that pair decorative even though it clears AA.
                  (pending
                    ? 'border border-dashed border-slate bg-paper text-ink'
                    : part.met
                      ? 'bg-success-tint text-forest'
                      : 'bg-paper text-slate')
                }
              >
                {pending ? <PendingGlyph /> : part.met ? <CheckGlyph /> : <DashGlyph />}
                {signalLabel(part)}
                <span className={pending ? undefined : 'tabular-nums'}>
                  {pending
                    ? 'noch nicht ausgewertet'
                    : `${part.met ? `+${part.points}` : '0'} Punkte`}
                </span>
              </span>
            </li>
          );
        })}
      </ul>

      {rawTotal > candidate.confidence ? (
        <p className="mt-2 text-xs text-slate">
          Die Einzelpunkte ergeben zusammen {rawTotal} Punkte; gewertet werden höchstens 100.
        </p>
      ) : null}
    </div>
  );
}

/**
 * State chip: icon plus text label, never tone alone (docs/05 § 2.5, BFSG).
 * Success is Forest Deep on Mint (10,01:1) rather than Green on Mint, which
 * docs/05 § 2.1 reserves for decoration.
 */
function StateChip({
  label,
  tone = 'neutral',
}: {
  label: string;
  tone?: 'neutral' | 'warning' | 'success';
}) {
  const surface =
    tone === 'warning'
      ? 'bg-warning-tint text-warning'
      : tone === 'success'
        ? 'bg-success-tint text-forest'
        : 'bg-paper text-slate';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold ${surface}`}
    >
      {tone === 'warning' ? <AlertGlyph /> : tone === 'success' ? <CheckGlyph /> : <InfoGlyph />}
      {label}
    </span>
  );
}
