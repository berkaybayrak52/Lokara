import { describe, expect, it } from 'vitest';
import { formatRechtsstand, getRule, RuleNotFoundError, type RuleSet } from './store';

const sample: RuleSet<number> = {
  key: 'sample.rate',
  versions: [
    { validFrom: '2020-01-01', validTo: '2023-01-01', source: 'v1', value: 10 },
    { validFrom: '2023-01-01', source: 'v2', value: 8 },
  ],
};

describe('getRule (as-of resolution)', () => {
  it('picks the version valid at the as-of date', () => {
    expect(getRule(sample, '2022-06-15').value).toBe(10);
    expect(getRule(sample, '2023-01-01').value).toBe(8);
    expect(getRule(sample, '2026-07-23').value).toBe(8);
  });

  it('stamps the Rechtsstand of the matched version', () => {
    expect(getRule(sample, '2024-05-01').rechtsstand).toBe('Rechtsstand 01/2023');
  });

  it('throws before the first version exists', () => {
    expect(() => getRule(sample, '2019-12-31')).toThrow(RuleNotFoundError);
  });
});

describe('formatRechtsstand', () => {
  it('formats MM/JJJJ', () => {
    expect(formatRechtsstand('2023-12-01')).toBe('Rechtsstand 12/2023');
  });
});
