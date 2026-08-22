import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { DemoStatementResponse } from '@/lib/contracts';

import { StatementResult } from './statement';

const RESULT: DemoStatementResponse = {
  buildingName: 'Musterhaus',
  buildingAddress: 'Musterstraße 12, 10115 Berlin',
  periodLabel: '01.01.2025 – 31.12.2025',
  nkCosts: [],
  nkTotalCents: 0,
  nkTotalEur: '0,00 €',
  nkInputTotalCents: 0,
  heatingLines: [],
  heatingTotalCents: 0,
  heatingTotalEur: '0,00 €',
  heatingInputTotalCents: 0,
  heatingMissingReason: null,
  // A self-billing run: the figures below are calculated by the engines, not
  // passed through from a confirmed Messdienstleister statement.
  heatingPath: 'SELF_BILLING',
  heatingSourceNote: null,
  heatingReadiness: 'READY',
  heatingFindings: [
    {
      code: 'device_estimate',
      message: 'Gerät HKV-1 wurde nach § 9a Abs. 1 HeizkostenV geschätzt.',
      severity: 'NOTICE',
      dismissible: false,
    },
  ],
  heatingProvenance: [
    {
      code: 'device_previous_period',
      source: 'HKV-1',
      detail: 'Vorjahreseinheiten wurden als Schätzgrundlage übernommen.',
    },
  ],
  heatingDeviceEvidence: [
    {
      deviceId: 'HKV-1',
      unitId: 'unit-a',
      room: 'Wohnzimmer',
      measurementUnit: 'HKV_UNITS',
      valuationFactor: '1,25',
      allocationKind: 'PARTY',
      targetId: 'tenancy-a',
      opening: null,
      closing: null,
      units: '125',
      estimated: true,
      estimationBasis: 'previous_period_units',
      readingReasons: ['PERIODIC'],
      readingSources: ['MDL'],
      provenanceRefs: ['MDL-Datei Zeile 17'],
    },
  ],
  heatingReductionRisks: [
    {
      code: 'remote_readability_missing',
      percent: '3',
      amountsEur: ['3,00 €'],
      message: 'Fernablesbare Ausstattung fehlt; kein automatischer Abzug.',
    },
    {
      code: 'section_6a_information_missing',
      percent: '3',
      amountsEur: ['3,00 €'],
      message: '§-6a-Informationen fehlen; kein automatischer Abzug.',
    },
  ],
  annualComparison: {
    state: 'RAW_FALLBACK',
    currentHeat: '1.100',
    previousHeat: '1.000',
    currentHeatAdjusted: null,
    previousHeatAdjusted: null,
    currentWarmWater: '20',
    previousWarmWater: '18',
    rawChangePercent: '10',
    adjustedChangePercent: null,
    graphRequired: true,
    note: 'DWD-Klimafaktor fehlt — Heizverbrauch wird ausdrücklich unbereinigt verglichen.',
  },
  co2: null,
  rechtsstaende: ['Rechtsstand 12/2025'],
  disclaimer: 'Keine Rechtsberatung.',
};

// The same run over a period that is not the seeded 2025 calendar year, with no
// cost types entered. `rechtsstaende` moves with the period so this fixture
// carries no other "2025" token — any that survives the render is hardcoded copy.
const EMPTY_COSTS_2024: DemoStatementResponse = {
  ...RESULT,
  periodLabel: '01.01.2024 – 30.06.2024',
  nkCosts: [],
  rechtsstaende: ['Rechtsstand 06/2024'],
};

describe('StatementResult Page 01b projection', () => {
  it('renders evidence, raw annual fallback, and each 3-percent risk separately', () => {
    const html = renderToStaticMarkup(
      <StatementResult data={RESULT} pdfUrl="/statement.pdf" accountId="acc-1" />,
    );

    expect(html).toContain('Geräte- und Ableseprotokoll');
    expect(html).toContain('DWD-Klimafaktor fehlt');
    expect(html).toContain('role="img"');
    expect(html.match(/3-%-Risiko/g)).toHaveLength(2);
    expect(html).not.toContain('6-%-Risiko');
  });

  it('names the object and the period it computed', () => {
    const html = renderToStaticMarkup(
      <StatementResult data={RESULT} pdfUrl="/statement.pdf" accountId="acc-1" />,
    );

    // Objekt und Zeitraum sind auf diesem Screen wählbar. Ein Ergebnis, das
    // seinen eigenen Bezug nicht nennt, lässt sich dem falschen Lauf zuordnen —
    // genau der Fehler, den das Zurücksetzen bei jeder Auswahl verhindern soll.
    expect(html).toContain('Musterhaus');
    expect(html).toContain('Musterstraße 12, 10115 Berlin');
    expect(html).toContain('Abrechnungszeitraum 01.01.2025 – 31.12.2025');
  });

  it('names the computed period in the empty-costs card, not a fixed year', () => {
    const html = renderToStaticMarkup(
      <StatementResult data={EMPTY_COSTS_2024} pdfUrl="/statement.pdf" accountId="acc-1" />,
    );

    expect(html).toContain('Für 01.01.2024 – 30.06.2024 sind noch keine Kostenarten erfasst');
    expect(html).not.toContain('2025');
  });
});
