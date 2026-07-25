import { describe, expect, it } from 'vitest';

import { centsToEurInput, isoToGermanDate, parseEurToCents, parseSqmToX100 } from './format';

describe('parseEurToCents', () => {
  it('parses German money formats', () => {
    expect(parseEurToCents('950')).toBe(95000);
    expect(parseEurToCents('950,5')).toBe(95050);
    expect(parseEurToCents('950,50')).toBe(95050);
    expect(parseEurToCents('1.234,56')).toBe(123456);
    expect(parseEurToCents('0,01')).toBe(1);
    expect(parseEurToCents(' 890,00 € ')).toBe(89000);
  });

  it('rejects ambiguous or non-German input', () => {
    expect(parseEurToCents('950.50')).toBeNull(); // dot is a thousands sep only
    expect(parseEurToCents('12,345')).toBeNull(); // 3 decimal places
    expect(parseEurToCents('abc')).toBeNull();
    expect(parseEurToCents('')).toBeNull();
    expect(parseEurToCents('-5')).toBeNull(); // no negative rents via forms
    expect(parseEurToCents('1.23,45')).toBeNull(); // malformed grouping
  });
});

describe('parseSqmToX100', () => {
  it('parses areas to fixed point', () => {
    expect(parseSqmToX100('64,5')).toBe(6450);
    expect(parseSqmToX100('64,50')).toBe(6450);
    expect(parseSqmToX100('120')).toBe(12000);
  });
});

describe('centsToEurInput', () => {
  it('round-trips with the parser', () => {
    for (const cents of [1, 95000, 95050, 123456]) {
      expect(parseEurToCents(centsToEurInput(cents))).toBe(cents);
    }
  });
});

describe('isoToGermanDate', () => {
  it('formats ISO dates', () => {
    expect(isoToGermanDate('2024-03-01')).toBe('01.03.2024');
  });
});
