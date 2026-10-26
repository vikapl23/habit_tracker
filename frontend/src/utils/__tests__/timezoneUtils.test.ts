import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  normalizeTimezone,
  getBrowserTimezone,
  getTimezoneOffsetString,
  formatTimezoneDisplay,
} from '../timezoneUtils';

describe('timezoneUtils', () => {
  const originalDateTimeFormat = Intl.DateTimeFormat;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    Intl.DateTimeFormat = originalDateTimeFormat;
  });

  it('normalizes Europe/Kiev to Europe/Kyiv', () => {
    expect(normalizeTimezone('Europe/Kiev')).toBe('Europe/Kyiv');
    expect(normalizeTimezone('Europe/Kyiv')).toBe('Europe/Kyiv');
    expect(normalizeTimezone('America/New_York')).toBe('America/New_York');
    expect(normalizeTimezone(null)).toBe('UTC');
    expect(normalizeTimezone(undefined)).toBe('UTC');
  });

  it('detects browser timezone and normalizes legacy names', () => {
    const mockResolved = vi.fn().mockReturnValue({ timeZone: 'Europe/Kiev' });
    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: mockResolved,
    } as unknown as Intl.DateTimeFormat);

    expect(getBrowserTimezone()).toBe('Europe/Kyiv');
  });

  it('formats timezone offset string correctly without depending on machine timezone', () => {
    const winterDate = new Date('2026-01-15T12:00:00Z');
    expect(getTimezoneOffsetString('Europe/Kyiv', winterDate)).toBe('UTC+02:00');
    expect(getTimezoneOffsetString('UTC', winterDate)).toBe('UTC+00:00');
    expect(getTimezoneOffsetString('America/New_York', winterDate)).toBe('UTC-05:00');
    expect(getTimezoneOffsetString('Asia/Kolkata', winterDate)).toBe('UTC+05:30');
  });

  it('formats timezone display name with offset', () => {
    const winterDate = new Date('2026-01-15T12:00:00Z');
    expect(formatTimezoneDisplay('Europe/Kyiv', winterDate)).toBe('Europe/Kyiv (UTC+02:00)');
    expect(formatTimezoneDisplay('Europe/Kiev', winterDate)).toBe('Europe/Kyiv (UTC+02:00)');
  });
});
