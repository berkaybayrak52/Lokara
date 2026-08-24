import { describe, expect, it } from 'vitest';

import {
  centsToEurDisplay,
  centsToEurInput,
  isoToGermanDate,
  meterValueToDisplay,
  parseEurToCents,
  parseMeterValueToX1000,
  parseSqmToX100,
} from './format';

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

describe('centsToEurDisplay', () => {
  it('formats amounts below the first separator with two decimals', () => {
    expect(centsToEurDisplay(0)).toBe('0,00 €');
    expect(centsToEurDisplay(1)).toBe('0,01 €');
    expect(centsToEurDisplay(50)).toBe('0,50 €');
    expect(centsToEurDisplay(20_005)).toBe('200,05 €'); // cents need zero-padding
    expect(centsToEurDisplay(95_000)).toBe('950,00 €');
    expect(centsToEurDisplay(99_999)).toBe('999,99 €'); // last ungrouped value
  });

  it('groups thousands with dots', () => {
    expect(centsToEurDisplay(100_000)).toBe('1.000,00 €'); // first grouped value
    expect(centsToEurDisplay(123_456)).toBe('1.234,56 €');
    expect(centsToEurDisplay(100_000_000)).toBe('1.000.000,00 €');
    expect(centsToEurDisplay(123_456_789_012)).toBe('1.234.567.890,12 €');
  });

  it('renders negatives with a leading minus (Stornobuchung)', () => {
    expect(centsToEurDisplay(-1)).toBe('-0,01 €');
    expect(centsToEurDisplay(-50)).toBe('-0,50 €');
    expect(centsToEurDisplay(-20_005)).toBe('-200,05 €');
    expect(centsToEurDisplay(-100_000)).toBe('-1.000,00 €');
    expect(centsToEurDisplay(-123_456)).toBe('-1.234,56 €');
    expect(centsToEurDisplay(-123_456_789_012)).toBe('-1.234.567.890,12 €');
  });

  it('stays distinct from the ungrouped, signless input format', () => {
    expect(centsToEurInput(123_456)).toBe('1234,56');
    expect(centsToEurDisplay(123_456)).toBe('1.234,56 €');
    expect(centsToEurInput(-123_456)).toBe('-1234,56');
    expect(centsToEurDisplay(-123_456)).toBe('-1.234,56 €');
    // the input variant is the one that has to round-trip back through the parser
    expect(parseEurToCents(centsToEurInput(123_456))).toBe(123_456);
  });
});

describe('isoToGermanDate', () => {
  it('formats ISO dates', () => {
    expect(isoToGermanDate('2024-03-01')).toBe('01.03.2024');
  });
});

describe('parseMeterValueToX1000', () => {
  it('parses register values to fixed point, up to 3 decimals', () => {
    expect(parseMeterValueToX1000('1800')).toBe(1_800_000);
    expect(parseMeterValueToX1000('1.800')).toBe(1_800_000); // thousands dot
    expect(parseMeterValueToX1000('241,5')).toBe(241_500);
    expect(parseMeterValueToX1000('168.500,25')).toBe(168_500_250);
    expect(parseMeterValueToX1000('0,001')).toBe(1); // one litre
  });

  it('rejects what money rejects, plus a 4th decimal', () => {
    expect(parseMeterValueToX1000('241.5')).toBeNull(); // dot is grouping only
    expect(parseMeterValueToX1000('1,2345')).toBeNull();
    expect(parseMeterValueToX1000('-5')).toBeNull(); // registers never run back
    expect(parseMeterValueToX1000('')).toBeNull();
  });
});

describe('meterValueToDisplay', () => {
  it('round-trips with the parser and drops trailing zeros', () => {
    expect(meterValueToDisplay(241_500)).toBe('241,5');
    expect(meterValueToDisplay(1_800_000)).toBe('1.800');
    expect(meterValueToDisplay(168_500_250)).toBe('168.500,25');
    for (const value of [1, 241_500, 1_800_000, 168_500_250]) {
      expect(parseMeterValueToX1000(meterValueToDisplay(value))).toBe(value);
    }
  });
});
