/**
 * Demo-/Mock-Finanzdaten fürs Dashboard (Spec 01_Dashboard.md, [D3]).
 *
 * WICHTIG: Diese Werte sind DEMO, nicht echt. Zahlungseingänge, offene Posten,
 * Cashflow-Historie und Ticket-Zahlen haben im heutigen Build keine Datenquelle
 * (Bankanbindung/finAPI verschoben, Mahnwesen und Ticket-Modul fehlen). Sie
 * werden hier deterministisch aus dem ECHTEN monatlichen Mietsoll abgeleitet,
 * damit alle Zahlen größenmäßig zueinander passen. Nichts davon wird gespeichert
 * oder fließt in eine Abrechnung ein.
 */

/** Fester Mock: Aufgaben-/Ticket-Zähler (Spec [D6]). */
export const DEMO_TASK_COUNTS = { overdue: 5, today: 10, week: 20 } as const;

/** Anteil des Mietsolls, der als „bereits eingegangen" gilt (Demo). */
const RECEIVED_SHARE = 0.82;
/** Ausgaben eines Monats als Anteil seiner Einnahmen (Demo). */
const EXPENSE_SHARE = 0.38;

/**
 * Feste Faktor-Reihe für die 12-Monats-Einnahmen (leichte Schwankung um 1,0);
 * der letzte (laufende) Monat ist bewusst niedriger, damit „noch nicht alles
 * eingegangen" sichtbar wird. Deterministisch, keine Zufallswerte.
 */
const CASHFLOW_FACTORS = [
  0.98, 1.02, 0.96, 1.05, 1.0, 0.94, 1.06, 1.01, 0.97, 1.04, 1.03, RECEIVED_SHARE,
] as const;

export interface DemoCashflowMonth {
  label: string;
  inCents: number;
  outCents: number;
  surplusCents: number;
}

export interface DemoFinance {
  receivedCents: number;
  openCents: number;
  openRenters: number;
  cashflow: DemoCashflowMonth[];
}

/**
 * Leitet aus dem echten `mietSollCentsMonthly` stimmige Demo-Finanzwerte ab.
 * Gleiche Eingabe → gleiche Ausgabe (bis auf die aus „heute" abgeleiteten
 * Monatskürzel).
 */
export function deriveDemoFinance(mietSollCentsMonthly: number): DemoFinance {
  const soll = Math.max(0, Math.round(mietSollCentsMonthly));
  const receivedCents = Math.round(soll * RECEIVED_SHARE);

  const now = new Date();
  const cashflow: DemoCashflowMonth[] = CASHFLOW_FACTORS.map((factor, index) => {
    const monthDate = new Date(now.getFullYear(), now.getMonth() - (CASHFLOW_FACTORS.length - 1 - index), 1);
    const label = monthDate.toLocaleDateString('de-DE', { month: 'short' }).replace('.', '');
    const inCents = Math.round(soll * factor);
    const outCents = Math.round(inCents * EXPENSE_SHARE);
    return { label, inCents, outCents, surplusCents: inCents - outCents };
  });

  return {
    receivedCents,
    openCents: soll - receivedCents,
    openRenters: 2,
    cashflow,
  };
}
