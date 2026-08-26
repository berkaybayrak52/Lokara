/**
 * Frontend-only Portfolio-Vorschau (DEMO-RUNBOOK-PORTFOLIO.md).
 *
 * WICHTIG: Dies ist reine Ansicht. Es ändert NICHTS am Backend, an der
 * Datenbank oder am Seed. Es fängt lediglich die Lese-Antworten der `api()`-
 * Funktion ab und liefert stattdessen synthetische Portfolio-Daten, damit man
 * sieht, wie Objekte- und Zahlungen-Seite mit dem größeren Demo-Datensatz
 * aussehen würden.
 *
 * Einschalten:
 *   - dauerhaft: `NEXT_PUBLIC_DEMO_PREVIEW=true` beim Start des Dev-Servers, ODER
 *   - im Browser: eine Seite mit `?preview=1` öffnen (bleibt per localStorage
 *     aktiv), mit `?preview=0` wieder ausschalten.
 *
 * Grenzen: Buttons wie „Bestätigen" buchen nichts (die POST-Antwort ist
 * ebenfalls synthetisch). Dashboard-Aggregate, Kosten, Zähler und Portal
 * laufen weiter gegen das echte Backend.
 */

import { ALLOCATION_KEY_LABELS, type AllocationKey } from './contracts';
import { centsToEurDisplay } from './format';

const PREVIEW_KEY = 'lokara:preview';

/** True, wenn der Vorschau-Modus aktiv ist. Client-seitig ausgewertet. */
export function isDemoPreview(): boolean {
  if (process.env.NEXT_PUBLIC_DEMO_PREVIEW === 'true') return true;
  if (typeof window === 'undefined') return false;
  try {
    const query = new URLSearchParams(window.location.search).get('preview');
    if (query === '1') {
      window.localStorage.setItem(PREVIEW_KEY, '1');
      return true;
    }
    if (query === '0') {
      window.localStorage.removeItem(PREVIEW_KEY);
      return false;
    }
    return window.localStorage.getItem(PREVIEW_KEY) === '1';
  } catch {
    return false;
  }
}

// ── Zeitachse relativ zu heute ─────────────────────────────────────────────
const NOW = new Date();

/** ISO-Datum (YYYY-MM-DD) für den Monat `offset` relativ zu heute, Tag `day`. */
function monthISO(offset: number, day = 1): string {
  return new Date(Date.UTC(NOW.getUTCFullYear(), NOW.getUTCMonth() + offset, day))
    .toISOString()
    .slice(0, 10);
}

/** Voller ISO-Zeitstempel für „erfasst am". */
function tsISO(offset: number, day: number): string {
  return new Date(
    Date.UTC(NOW.getUTCFullYear(), NOW.getUTCMonth() + offset, day, 9, 0, 0),
  ).toISOString();
}

/** Periodenlabel „YYYY-MM" für den Monat `offset`. */
function periodLabel(offset: number): string {
  const d = new Date(Date.UTC(NOW.getUTCFullYear(), NOW.getUTCMonth() + offset, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

const eur = (cents: number): string => centsToEurDisplay(cents);

// ── Objekte und Einheiten ──────────────────────────────────────────────────
interface UnitSpec {
  id: string;
  label: string;
  areaSqm: number;
  occupied: boolean;
}
interface BuildingSpec {
  id: string;
  name: string;
  street: string;
  postalCode: string;
  city: string;
  buildingType: string;
  lat: number | null;
  lon: number | null;
  units: UnitSpec[];
}

const BUILDINGS: BuildingSpec[] = [
  {
    id: 'bld_prev_muster',
    name: 'Musterstraße 12',
    street: 'Musterstraße 12',
    postalCode: '60311',
    city: 'Frankfurt am Main',
    buildingType: 'WOHN_UND_GESCHAEFTSHAUS',
    lat: 50.1109,
    lon: 8.6821,
    units: [
      { id: 'u_muster_a', label: 'Wohnung A · EG links', areaSqm: 50, occupied: true },
      { id: 'u_muster_b', label: 'Wohnung B · EG rechts', areaSqm: 30, occupied: true },
      { id: 'u_muster_c', label: 'Wohnung C · 1. OG links', areaSqm: 20, occupied: true },
      { id: 'u_muster_d', label: 'Wohnung D · 1. OG rechts', areaSqm: 45, occupied: true },
      { id: 'u_muster_dg', label: 'Dachgeschoss', areaSqm: 62, occupied: true },
      { id: 'u_muster_laden', label: 'Ladenlokal (Gewerbe)', areaSqm: 78, occupied: true },
    ],
  },
  {
    id: 'bld_prev_linden',
    name: 'Lindenweg 8',
    street: 'Lindenweg 8',
    postalCode: '55116',
    city: 'Mainz',
    buildingType: 'WOHNHAUS',
    lat: 49.9929,
    lon: 8.2473,
    units: [
      { id: 'u_linden_1', label: 'Wohnung 1 · EG', areaSqm: 58, occupied: true },
      { id: 'u_linden_2', label: 'Wohnung 2 · 1. OG', areaSqm: 49, occupied: true },
      { id: 'u_linden_3', label: 'Wohnung 3 · 2. OG', areaSqm: 66, occupied: true },
      { id: 'u_linden_elw', label: 'Einliegerwohnung', areaSqm: 42, occupied: false },
    ],
  },
  {
    id: 'bld_prev_hafen',
    name: 'Hafenallee 27',
    street: 'Hafenallee 27',
    postalCode: '65183',
    city: 'Wiesbaden',
    buildingType: 'WOHN_UND_GESCHAEFTSHAUS',
    lat: 50.0782,
    lon: 8.2398,
    units: [
      { id: 'u_hafen_l1', label: 'Loft 1', areaSqm: 82, occupied: true },
      { id: 'u_hafen_l2', label: 'Loft 2', areaSqm: 74, occupied: true },
      { id: 'u_hafen_buero', label: 'Büroeinheit (Gewerbe)', areaSqm: 132, occupied: true },
    ],
  },
];

// ── Parteien ───────────────────────────────────────────────────────────────
interface Party {
  renterId: string;
  tenancyId: string;
  unitId: string;
  name: string;
  base: number;
  nk: number;
  heating: number;
  bank: string;
  /** Monat (negativ), ab dem die Partei zahlt; sehr klein = „schon lange". */
  startOffset: number;
}

const WOHNEN = 'bank_prev_wohnen';
const HAFEN = 'bank_prev_hafen';

const PARTIES: Party[] = [
  { renterId: 'r_anna', tenancyId: 't_anna', unitId: 'u_muster_a', name: 'Anna Beispiel', base: 95000, nk: 16000, heating: 6000, bank: WOHNEN, startOffset: -60 },
  { renterId: 'r_fatma', tenancyId: 't_fatma', unitId: 'u_muster_b', name: 'Fatma Yilmaz', base: 68000, nk: 11000, heating: 4000, bank: WOHNEN, startOffset: -5 },
  { renterId: 'r_clara', tenancyId: 't_clara', unitId: 'u_muster_c', name: 'Clara Vorlage', base: 52000, nk: 8000, heating: 3000, bank: WOHNEN, startOffset: -60 },
  { renterId: 'r_david', tenancyId: 't_david', unitId: 'u_muster_d', name: 'David Sommer', base: 78000, nk: 14000, heating: 5000, bank: WOHNEN, startOffset: -60 },
  { renterId: 'r_eva', tenancyId: 't_eva', unitId: 'u_muster_dg', name: 'Eva König', base: 110000, nk: 18000, heating: 7000, bank: WOHNEN, startOffset: -23 },
  { renterId: 'r_kiez', tenancyId: 't_kiez', unitId: 'u_muster_laden', name: 'Kiez Café GmbH', base: 145000, nk: 22000, heating: 8000, bank: WOHNEN, startOffset: -60 },
  { renterId: 'r_jonas', tenancyId: 't_jonas', unitId: 'u_linden_1', name: 'Jonas Weber', base: 89000, nk: 15500, heating: 5500, bank: WOHNEN, startOffset: -40 },
  { renterId: 'r_lea', tenancyId: 't_lea', unitId: 'u_linden_2', name: 'Lea Neumann', base: 76000, nk: 13000, heating: 5000, bank: WOHNEN, startOffset: -30 },
  { renterId: 'r_maria', tenancyId: 't_maria', unitId: 'u_linden_3', name: 'Maria Santos', base: 99000, nk: 16500, heating: 6500, bank: WOHNEN, startOffset: -28 },
  { renterId: 'r_noah', tenancyId: 't_noah', unitId: 'u_hafen_l1', name: 'Noah Richter', base: 125000, nk: 20000, heating: 8000, bank: HAFEN, startOffset: -30 },
  { renterId: 'r_sophie', tenancyId: 't_sophie', unitId: 'u_hafen_l2', name: 'Sophie Klein', base: 108000, nk: 17500, heating: 6500, bank: HAFEN, startOffset: -30 },
  { renterId: 'r_rheinblick', tenancyId: 't_rheinblick', unitId: 'u_hafen_buero', name: 'Rheinblick Design UG', base: 210000, nk: 33000, heating: 12000, bank: HAFEN, startOffset: -50 },
];

const soll = (p: Party): number => p.base + p.nk + p.heating;
const partyByUnit = (unitId: string): Party | undefined => PARTIES.find((p) => p.unitId === unitId);

// ── Vormieter Wohnung B (Mieterwechsel) ────────────────────────────────────
const BERND = { renterId: 'r_bernd', tenancyId: 't_bernd', name: 'Bernd Muster', amount: 83000 };

// ── Generatoren ────────────────────────────────────────────────────────────
type Json = Record<string, unknown>;

function allocation(id: string, receivableId: string, p: Party, amount: number, status: string): Json {
  const settled = status === 'settled';
  return {
    id,
    receivable_id: receivableId,
    costs_cents: 0,
    interest_cents: 0,
    principal_cents: amount,
    components: {
      base_rent_cents: settled ? p.base : amount,
      nk_advance_cents: settled ? p.nk : 0,
      heating_advance_cents: settled ? p.heating : 0,
      garage_cents: 0,
    },
    resulting_status: status,
    before: { open_costs_cents: 0, open_interest_cents: 0, open_principal_cents: soll(p), open_cents: soll(p), status: 'open' },
    after: {
      open_costs_cents: 0,
      open_interest_cents: 0,
      open_principal_cents: soll(p) - amount,
      open_cents: soll(p) - amount,
      status,
    },
  };
}

interface Generated {
  ledger: Json[];
  receivables: Json[];
  transactions: Json[];
  proposals: Json[];
}

function generate(): Generated {
  const ledger: Json[] = [];
  const receivables: Json[] = [];
  const transactions: Json[] = [];
  const proposals: Json[] = [];
  let order = 0;

  // Historie M-12 … M-1: reguläre, automatisch gebuchte Mieten.
  for (let offset = -12; offset <= -1; offset++) {
    for (const p of PARTIES) {
      // Wohnung B: Bernd (M-8/-7), Leerstand (M-6), Fatma (ab M-5).
      if (p.unitId === 'u_muster_b') {
        if (offset === -6) continue; // Leerstandsmonat: keine Forderung
        if (offset < -5) {
          const recId = `rec_bernd_${offset}`;
          receivables.push(rentReceivable(recId, BERND.renterId, BERND.tenancyId, offset, BERND.amount, 0, 'settled'));
          ledger.push(rentLedger(`led_bernd_${offset}`, offset, order++, { ...p, base: BERND.amount, nk: 0, heating: 0 }, recId, BERND.amount, 'settled'));
          continue;
        }
      }
      if (offset < p.startOffset) continue;

      const recId = `rec_${p.renterId}_${offset}`;
      receivables.push(rentReceivable(recId, p.renterId, p.tenancyId, offset, soll(p), 0, 'settled'));
      ledger.push(rentLedger(`led_${p.renterId}_${offset}`, offset, order++, p, recId, soll(p), 'settled'));
    }
  }

  // Sonderfall David: Rücklastschrift in M-2 + Ersatzüberweisung.
  const david = partyByUnit('u_muster_d')!;
  ledger.push({
    id: 'led_david_reversal',
    bank_transaction_id: 'btx_david_reversal',
    match_proposal_id: 'mp_david_reversal',
    kind: 'reversal',
    amount_cents: -soll(david),
    credit_cents: 0,
    ordering_version: order++,
    reverses_entry_id: 'led_r_david_-2',
    created_at: tsISO(-2, 14),
    allocations: [],
  });
  ledger.push(rentLedger('led_david_ersatz', -2, order++, david, 'rec_r_david_-2', soll(david), 'settled'));

  // Anna: offene Betriebskosten-Nachzahlung 245,00 €, davon 120,00 € bar in M-1.
  receivables.push({
    id: 'rec_anna_nk',
    renter_id: 'r_anna',
    tenancy_id: 't_anna',
    source_type: 'nk_settlement',
    source_id: null,
    period: periodLabel(0),
    due_date: monthISO(0, 15),
    expected_cents: 24500,
    open_cents: 12500,
    status: 'partial',
    category: 'nk_nachzahlung',
  });
  ledger.push({
    id: 'led_anna_cash',
    bank_transaction_id: 'btx_anna_cash',
    match_proposal_id: 'mp_anna_cash',
    kind: 'payment',
    amount_cents: 12000,
    credit_cents: 0,
    ordering_version: order++,
    reverses_entry_id: null,
    created_at: tsISO(-1, 20),
    allocations: [
      {
        id: 'alloc_anna_cash',
        receivable_id: 'rec_anna_nk',
        costs_cents: 12000,
        interest_cents: 0,
        principal_cents: 0,
        components: { base_rent_cents: 0, nk_advance_cents: 0, heating_advance_cents: 0, garage_cents: 0 },
        resulting_status: 'partial',
        before: { open_costs_cents: 24500, open_interest_cents: 0, open_principal_cents: 0, open_cents: 24500, status: 'open' },
        after: { open_costs_cents: 12500, open_interest_cents: 0, open_principal_cents: 0, open_cents: 12500, status: 'partial' },
      },
    ],
  });

  // Laufender Monat M0.
  const anna = partyByUnit('u_muster_a')!;
  const noah = partyByUnit('u_hafen_l1')!;
  const autoBookedM0 = PARTIES.filter((p) =>
    ['r_anna', 'r_fatma', 'r_clara', 'r_david', 'r_kiez', 'r_lea', 'r_noah', 'r_rheinblick'].includes(p.renterId),
  );
  for (const p of autoBookedM0) {
    const recId = `rec_${p.renterId}_0`;
    receivables.push(rentReceivable(recId, p.renterId, p.tenancyId, 0, soll(p), 0, 'settled'));
    ledger.push(rentLedger(`led_${p.renterId}_0`, 0, order++, p, recId, soll(p), 'settled'));
  }

  // Jonas: Teilzahlung 600,00 € auf 1.100,00 €.
  const jonas = partyByUnit('u_linden_1')!;
  receivables.push(rentReceivable('rec_jonas_0', jonas.renterId, jonas.tenancyId, 0, soll(jonas), 50000, 'partial'));
  ledger.push({
    id: 'led_jonas_0',
    bank_transaction_id: 'btx_jonas_0',
    match_proposal_id: 'mp_jonas_0',
    kind: 'payment',
    amount_cents: 60000,
    credit_cents: 0,
    ordering_version: order++,
    reverses_entry_id: null,
    created_at: tsISO(0, 4),
    allocations: [allocation('alloc_jonas_0', 'rec_jonas_0', jonas, 60000, 'partial')],
  });

  // Offene M0-Forderungen ohne Buchung: Sophie (kein Eingang), Eva/Maria (Prüfung).
  const sophie = partyByUnit('u_hafen_l2')!;
  receivables.push(rentReceivable('rec_sophie_0', sophie.renterId, sophie.tenancyId, 0, soll(sophie), soll(sophie), 'open'));
  const eva = partyByUnit('u_muster_dg')!;
  receivables.push(rentReceivable('rec_eva_0', eva.renterId, eva.tenancyId, 0, soll(eva), soll(eva), 'open'));
  const maria = partyByUnit('u_linden_3')!;
  receivables.push(rentReceivable('rec_maria_0', maria.renterId, maria.tenancyId, 0, soll(maria), soll(maria), 'open'));

  // ── Zuordnung prüfen (Bankumsätze + Vorschläge) ──────────────────────────
  // Eva — Betrag/Zeitraum passen, Absender weicht ab → Prüfung.
  transactions.push(btx('btx_eva_0', eva.bank, soll(eva), monthISO(0, 2), 'E. König-Fischer', 'Miete Wohnung DG', false));
  proposals.push({
    transaction_id: 'btx_eva_0',
    decision: 'needs_review',
    reason_de: 'Betrag und Zeitraum passen, aber der Absendername weicht vom üblichen Konto ab.',
    candidates: [candidate('mp_eva_0', 'rec_eva_0', 'r_eva', { iban: 0, amount: 30, code_or_surname: 20, end_to_end: 0, period: 20 }, 70)],
    confirmation: null,
    ledger_entry_id: null,
    created_at: tsISO(0, 2),
  });

  // Maria — 100,00 € über der offenen Forderung → Prüfung.
  transactions.push(btx('btx_maria_0', maria.bank, soll(maria) + 10000, monthISO(0, 3), 'Maria Santos', 'Miete', false));
  proposals.push({
    transaction_id: 'btx_maria_0',
    decision: 'needs_review',
    reason_de: 'Zahlung liegt 100,00 € über der offenen Forderung — bitte prüfen.',
    candidates: [candidate('mp_maria_0', 'rec_maria_0', 'r_maria', { iban: 40, amount: 0, code_or_surname: 20, end_to_end: 0, period: 20 }, 80)],
    confirmation: null,
    ledger_entry_id: null,
    created_at: tsISO(0, 3),
  });

  // Nicht zuzuordnender Eingang.
  transactions.push(btx('btx_emir_0', WOHNEN, 5000, monthISO(0, 6), 'Emir P.', 'Überweisung', false));
  proposals.push({
    transaction_id: 'btx_emir_0',
    decision: 'unmatched',
    reason_de: 'Kein Zahlungscode und kein passender Betrag gefunden.',
    candidates: [candidate('mp_emir_0', null, null, { iban: 0, amount: 0, code_or_surname: 0, end_to_end: 0, period: 0 }, 0)],
    confirmation: null,
    ledger_entry_id: null,
    created_at: tsISO(0, 6),
  });

  // Kiez Café — mögliche Dublette.
  transactions.push(btx('btx_kiez_dup', WOHNEN, 175000, monthISO(0, 5), 'Kiez Café GmbH', 'Miete Ladenlokal', true));
  proposals.push({
    transaction_id: 'btx_kiez_dup',
    decision: 'deduped',
    reason_de: 'Wurde in diesem Zeitraum bereits importiert — mögliche Dublette.',
    candidates: [],
    confirmation: null,
    ledger_entry_id: null,
    created_at: tsISO(0, 5),
  });

  // Bereits automatisch gebuchte M0-Umsätze als Nachweis in der Prüfliste.
  transactions.push(btx('btx_anna_0', anna.bank, soll(anna), monthISO(0, 1), 'Anna Beispiel', 'Miete', false));
  proposals.push({
    transaction_id: 'btx_anna_0',
    decision: 'auto_match',
    reason_de: 'Eindeutige IBAN und exakter Betrag.',
    candidates: [candidate('mp_anna_0c', 'rec_r_anna_0', 'r_anna', { iban: 40, amount: 30, code_or_surname: 20, end_to_end: 0, period: 20 }, 100)],
    confirmation: null,
    ledger_entry_id: 'led_r_anna_0',
    created_at: tsISO(0, 1),
  });
  transactions.push(btx('btx_noah_0', noah.bank, soll(noah), monthISO(0, 1), 'Noah Richter', 'Miete Loft 1', false));
  proposals.push({
    transaction_id: 'btx_noah_0',
    decision: 'auto_match',
    reason_de: 'Eindeutige IBAN und exakter Betrag.',
    candidates: [candidate('mp_noah_0c', 'rec_r_noah_0', 'r_noah', { iban: 40, amount: 30, code_or_surname: 20, end_to_end: 0, period: 20 }, 100)],
    confirmation: null,
    ledger_entry_id: 'led_r_noah_0',
    created_at: tsISO(0, 1),
  });

  // Neueste zuerst.
  ledger.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  return { ledger, receivables, transactions, proposals };
}

function rentReceivable(
  id: string,
  renterId: string,
  tenancyId: string,
  offset: number,
  expected: number,
  open: number,
  status: string,
): Json {
  return {
    id,
    renter_id: renterId,
    tenancy_id: tenancyId,
    source_type: 'monthly_rent',
    source_id: null,
    period: periodLabel(offset),
    due_date: monthISO(offset, 3),
    expected_cents: expected,
    open_cents: open,
    status,
    category: 'rent',
  };
}

function rentLedger(
  id: string,
  offset: number,
  order: number,
  p: Party,
  receivableId: string,
  amount: number,
  status: string,
): Json {
  return {
    id,
    bank_transaction_id: `btx_${id}`,
    match_proposal_id: `mp_${id}`,
    kind: 'payment',
    amount_cents: amount,
    credit_cents: 0,
    ordering_version: order,
    reverses_entry_id: null,
    created_at: tsISO(offset, 4),
    allocations: [allocation(`alloc_${id}`, receivableId, p, amount, status)],
  };
}

function btx(
  id: string,
  bankAccountId: string,
  amount: number,
  date: string,
  counterpart: string,
  purpose: string,
  duplicate: boolean,
): Json {
  return {
    id,
    bank_account_id: bankAccountId,
    provider_transaction_id: `finapi-demo-${id}`,
    amount_cents: amount,
    bank_booking_date: date,
    counterpart_name: counterpart,
    purpose,
    is_potential_duplicate: duplicate,
  };
}

function candidate(
  proposalId: string,
  receivableId: string | null,
  renterId: string | null,
  signals: { iban: number; amount: number; code_or_surname: number; end_to_end: number; period: number },
  confidence: number,
): Json {
  return { proposal_id: proposalId, rank: 1, receivable_id: receivableId, renter_id: renterId, signals, confidence };
}

let cache: Generated | null = null;
function data(): Generated {
  cache ??= generate();
  return cache;
}

// ── Objekt-/Einheiten-Antworten ────────────────────────────────────────────
function tenanciesForUnit(unitId: string): Json[] {
  // Mieterwechsel Wohnung B: beendetes Bernd-Verhältnis + aktives Fatma.
  if (unitId === 'u_muster_b') {
    return [
      {
        id: 't_bernd',
        renterNames: ['Bernd Muster'],
        validFrom: monthISO(-40, 1),
        validTo: monthISO(-6, 1),
        baseRentCents: 66000,
        baseRentEur: eur(66000),
        advancePaymentSchedule: [advPeriod('app_bernd', 17000, monthISO(-40, 1), monthISO(-6, 1))],
        activeToday: false,
      },
      tenancyRow(partyByUnit(unitId)!),
    ];
  }
  // Einliegerwohnung: nur beendetes Verhältnis, aktuell Leerstand.
  if (unitId === 'u_linden_elw') {
    return [
      {
        id: 't_elw_alt',
        renterNames: ['Vormieter (ausgezogen)'],
        validFrom: monthISO(-30, 1),
        validTo: monthISO(-2, 1),
        baseRentCents: 65000,
        baseRentEur: eur(65000),
        advancePaymentSchedule: [advPeriod('app_elw', 16000, monthISO(-30, 1), monthISO(-2, 1))],
        activeToday: false,
      },
    ];
  }
  const p = partyByUnit(unitId);
  return p ? [tenancyRow(p)] : [];
}

function advPeriod(id: string, amount: number, validFrom: string, validTo: string | null): Json {
  return {
    id,
    amountCents: amount,
    amountEur: eur(amount),
    validFrom,
    validTo,
    predecessorId: null,
    declarationRef: 'Demo-Mietvertrag',
  };
}

function tenancyRow(p: Party): Json {
  return {
    id: p.tenancyId,
    renterNames: [p.name],
    validFrom: monthISO(p.startOffset, 1),
    validTo: null,
    baseRentCents: p.base,
    baseRentEur: eur(p.base),
    advancePaymentSchedule: [
      advPeriod(`app_${p.tenancyId}`, p.nk + p.heating, monthISO(p.startOffset, 1), null),
    ],
    activeToday: true,
  };
}

function buildingList(): Json {
  return {
    buildings: BUILDINGS.map((b) => ({
      id: b.id,
      name: b.name,
      street: b.street,
      postalCode: b.postalCode,
      city: b.city,
      unitCount: b.units.length,
      buildingType: b.buildingType,
      latitude: b.lat,
      longitude: b.lon,
    })),
  };
}

function buildingDetail(buildingId: string): Json | undefined {
  const b = BUILDINGS.find((x) => x.id === buildingId);
  if (!b) return undefined;
  return {
    id: b.id,
    name: b.name,
    street: b.street,
    postalCode: b.postalCode,
    city: b.city,
    units: b.units.map((u) => ({
      id: u.id,
      label: u.label,
      areaSqm: u.areaSqm,
      tenancyCount: tenanciesForUnit(u.id).length,
      occupiedToday: u.occupied,
    })),
  };
}

function unitDetail(unitId: string): Json | undefined {
  for (const b of BUILDINGS) {
    const u = b.units.find((x) => x.id === unitId);
    if (u) {
      return {
        id: u.id,
        label: u.label,
        areaSqm: u.areaSqm,
        buildingId: b.id,
        buildingName: b.name,
        tenancies: tenanciesForUnit(u.id),
        selfUsePeriods: [],
      };
    }
  }
  return undefined;
}

// ── Dashboard-Aggregat ─────────────────────────────────────────────────────
function portfolioOverview(): Json {
  const unitCount = BUILDINGS.reduce((sum, b) => sum + b.units.length, 0);
  const vacant = BUILDINGS.reduce((sum, b) => sum + b.units.filter((u) => !u.occupied).length, 0);
  const mietSoll = PARTIES.reduce((sum, p) => sum + soll(p), 0);
  return {
    buildingCount: BUILDINGS.length,
    unitCount,
    occupiedUnitCount: unitCount - vacant,
    vacantUnitCount: vacant,
    mietSollCentsMonthly: mietSoll,
  };
}

// ── Kosten (Y-1) ───────────────────────────────────────────────────────────
const YEAR = NOW.getUTCFullYear() - 1;
const Y1_FROM = `${YEAR}-01-01`;
const Y1_TO = `${YEAR}-12-31`;

function cost(id: string, label: string, cents: number, key: AllocationKey): Json {
  return {
    id,
    label,
    amountCents: cents,
    amountEur: eur(cents),
    periodFrom: Y1_FROM,
    periodTo: Y1_TO,
    key,
    keyLabel: ALLOCATION_KEY_LABELS[key],
    directUnitId: null,
    directTenancyId: null,
    assignmentCount: 1,
  };
}

const COSTS: Record<string, Json[]> = {
  bld_prev_muster: [
    cost('c_m_muell', 'Müllabfuhr', 120000, 'AREA'),
    cost('c_m_versicherung', 'Gebäudeversicherung', 98000, 'AREA'),
    cost('c_m_reinigung', 'Hausreinigung Treppenhaus', 64000, 'UNITS'),
    cost('c_m_strom', 'Allgemeinstrom', 31000, 'AREA'),
  ],
  bld_prev_linden: [
    cost('c_l_wasser', 'Wasser/Abwasser', 145000, 'CONSUMPTION'),
    cost('c_l_muell', 'Müllabfuhr', 72000, 'AREA'),
    cost('c_l_versicherung', 'Gebäudeversicherung', 81000, 'AREA'),
    cost('c_l_garten', 'Gartenpflege', 48000, 'AREA'),
  ],
  bld_prev_hafen: [
    cost('c_h_versicherung', 'Gebäudeversicherung', 132000, 'AREA'),
    cost('c_h_aufzug', 'Aufzugswartung', 118000, 'UNITS'),
    cost('c_h_reinigung', 'Reinigung', 89000, 'UNITS'),
    cost('c_h_strom', 'Allgemeinstrom', 54000, 'AREA'),
  ],
};

// ── Zähler ─────────────────────────────────────────────────────────────────
const SYMBOL: Record<string, string> = { KWH: 'kWh', CUBIC_METRE: 'm³', HKV_UNITS: 'Einh.' };

function fmt(valueX1000: number, symbol: string): string {
  return `${(valueX1000 / 1000).toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: 3 })} ${symbol}`;
}

function reading(id: string, iso: string, valueX1000: number, symbol: string): Json {
  return {
    id,
    readAt: iso,
    valueX1000,
    valueDisplay: fmt(valueX1000, symbol),
    reason: 'PERIODIC',
    source: 'MDL',
    note: null,
    tenancyId: null,
    estimatedConsumptionX1000: null,
    estimationBasis: null,
    provenanceRef: null,
    recordedAt: `${iso}T09:00:00.000Z`,
    superseded: false,
  };
}

function meter(
  id: string,
  unitId: string | null,
  unitLabel: string | null,
  kind: string,
  kindLabel: string,
  mUnit: string,
  serial: string,
  label: string | null,
  calibrationValidUntil: string | null,
  calibrationStatus: string,
  factorX1000: number | null,
  open: number,
  close: number,
): Json {
  const symbol = SYMBOL[mUnit] ?? '';
  return {
    id,
    unitId,
    unitLabel,
    kind,
    kindLabel,
    measurementUnit: mUnit,
    unitSymbol: symbol,
    serial,
    label,
    calibrationValidUntil,
    valuationFactorX1000: factorX1000,
    valuationFactorDisplay: factorX1000 === null ? null : (factorX1000 / 1000).toLocaleString('de-DE'),
    calibrationStatus,
    readings: [reading(`${id}_open`, Y1_FROM, open, symbol), reading(`${id}_close`, Y1_TO, close, symbol)],
    periodConsumptionDisplay: fmt(close - open, symbol),
  };
}

const METERS: Record<string, Json[]> = {
  bld_prev_muster: [
    meter('m_m_heat', null, null, 'HEAT', 'Wärme', 'KWH', 'WMZ-2022-004711', 'Wärmemengenzähler Heizzentrale', '2027-12-31', 'VALID', 1000, 148_500_000, 168_500_000),
    meter('m_m_ww', null, null, 'WARM_WATER', 'Warmwasser', 'CUBIC_METRE', 'WWZ-2022-118342', 'Warmwasserzähler Heizzentrale', '2028-12-31', 'VALID', null, 812_000, 852_000),
    meter('m_m_hkv_a', 'u_muster_a', 'Wohnung A · EG links', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-A-100231', null, null, 'NOT_APPLICABLE', 1000, 1_200_000, 1_800_000),
    meter('m_m_hkv_b', 'u_muster_b', 'Wohnung B · EG rechts', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-B-100232', null, null, 'NOT_APPLICABLE', 1000, 3_400_000, 3_650_000),
    meter('m_m_kw_c', 'u_muster_c', 'Wohnung C · 1. OG links', 'COLD_WATER', 'Kaltwasser', 'CUBIC_METRE', 'KWZ-C-441097', null, '2025-12-31', 'EXPIRED', null, 302_400, 340_900),
  ],
  bld_prev_linden: [
    meter('m_l_heat', null, null, 'HEAT', 'Wärme', 'KWH', 'WMZ-2021-220145', 'Hauptwärmezähler', '2027-12-31', 'VALID', 1000, 61_000_000, 78_400_000),
    meter('m_l_hkv_1', 'u_linden_1', 'Wohnung 1 · EG', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-LW1-3301', null, null, 'NOT_APPLICABLE', 1000, 0, 720_000),
    meter('m_l_hkv_2', 'u_linden_2', 'Wohnung 2 · 1. OG', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-LW2-3302', null, null, 'NOT_APPLICABLE', 1000, 0, 540_000),
    meter('m_l_hkv_3', 'u_linden_3', 'Wohnung 3 · 2. OG', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-LW3-3303', null, null, 'NOT_APPLICABLE', 1000, 0, 810_000),
  ],
  bld_prev_hafen: [
    meter('m_h_heat', null, null, 'HEAT', 'Wärme', 'KWH', 'WMZ-2020-559120', 'Hauptwärmezähler', '2026-11-30', 'EXPIRING_SOON', 1000, 92_000_000, 118_600_000),
    meter('m_h_ww', null, null, 'WARM_WATER', 'Warmwasser', 'CUBIC_METRE', 'WWZ-2023-771204', 'Warmwasserzähler', '2029-12-31', 'VALID', null, 410_000, 468_000),
    meter('m_h_hkv_l1', 'u_hafen_l1', 'Loft 1', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-HA-L1', null, null, 'NOT_APPLICABLE', 1000, 0, 940_000),
    meter('m_h_hkv_l2', 'u_hafen_l2', 'Loft 2', 'HEAT', 'Wärme', 'HKV_UNITS', 'HKV-HA-L2', null, null, 'NOT_APPLICABLE', 1000, 0, 815_000),
  ],
};

function heatingCost(id: string, label: string, cents: number, co2Kg: number | null, co2Cost: number | null): Json {
  return {
    id,
    label,
    amountCents: cents,
    amountEur: eur(cents),
    periodFrom: Y1_FROM,
    periodTo: Y1_TO,
    co2KgX1000: co2Kg === null ? null : co2Kg * 1000,
    co2KgDisplay: co2Kg === null ? null : co2Kg.toLocaleString('de-DE'),
    co2CostCents: co2Cost,
    co2CostEur: co2Cost === null ? null : eur(co2Cost),
  };
}

const HEATING_COSTS: Record<string, Json[]> = {
  bld_prev_muster: [heatingCost('hc_m', 'Heizung & Warmwasser (Brennstoff, Wartung, Betriebsstrom)', 1_030_000, 4000, 26180)],
  bld_prev_linden: [heatingCost('hc_l', 'Heizung & Warmwasser', 680_000, 2600, 17020)],
  bld_prev_hafen: [heatingCost('hc_h', 'Heizung & Warmwasser', 940_000, 3600, 23560)],
};

/**
 * Liefert eine synthetische Antwort für `path`, oder `undefined`, wenn der
 * Vorschau-Modus diesen Pfad nicht kennt (dann läuft der echte Fetch).
 */
export function previewResponse(path: string, init?: RequestInit): unknown {
  const method = (init?.method ?? 'GET').toUpperCase();
  const clean = path.split('?')[0] ?? path;

  if (method === 'GET') {
    if (clean === '/me') {
      return {
        personId: 'per_demo_owner',
        email: 'demo@lokara.example',
        accounts: [
          { id: 'acc_demo_lokara', name: 'Demo Portfolio', role: 'OWNER', shape: 'HAUSVERWALTUNG' },
        ],
      };
    }
    if (/\/a\/[^/]+\/portfolio\/overview$/.test(clean)) return portfolioOverview();
    if (/\/a\/[^/]+\/buildings$/.test(clean)) return buildingList();
    const costs = clean.match(/\/a\/[^/]+\/buildings\/([^/]+)\/costs$/);
    if (costs?.[1]) return { costs: COSTS[costs[1]] ?? [] };
    const meters = clean.match(/\/a\/[^/]+\/buildings\/([^/]+)\/meters$/);
    if (meters?.[1]) return { meters: METERS[meters[1]] ?? [], periodLabel: `01.01.${YEAR} – 31.12.${YEAR}` };
    const heating = clean.match(/\/a\/[^/]+\/buildings\/([^/]+)\/heating-costs$/);
    if (heating?.[1]) return { heatingCosts: HEATING_COSTS[heating[1]] ?? [] };
    const bDetail = clean.match(/\/a\/[^/]+\/buildings\/([^/]+)$/);
    if (bDetail?.[1]) return buildingDetail(bDetail[1]);
    const uDetail = clean.match(/\/a\/[^/]+\/units\/([^/]+)$/);
    if (uDetail?.[1]) return unitDetail(uDetail[1]);
    if (/\/a\/[^/]+\/match-proposals$/.test(clean)) return { transactions: data().proposals };
    if (/\/a\/[^/]+\/bank-transactions$/.test(clean)) return { transactions: data().transactions };
    if (/\/a\/[^/]+\/receivables$/.test(clean)) return { receivables: data().receivables };
    if (/\/a\/[^/]+\/payment-ledger$/.test(clean)) return { entries: data().ledger };
  }

  // Entscheidungs-POST: synthetische Erfolgsantwort, damit ein Klick nicht crasht.
  const decision = clean.match(/\/a\/[^/]+\/bank-transactions\/([^/]+)\/decision$/);
  if (method === 'POST' && decision?.[1]) {
    let outcome = 'confirmed';
    try {
      const body = JSON.parse(String(init?.body ?? '{}')) as { outcome?: string };
      if (body.outcome) outcome = body.outcome;
    } catch {
      /* leerer Body */
    }
    return { transaction_id: decision[1], outcome, selected_rank: 1, ledger_entry_id: null };
  }

  return undefined;
}
