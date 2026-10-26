export const normalizeTimezone = (tz: string | null | undefined): string => {
  if (!tz) return 'UTC';
  if (tz === 'Europe/Kiev') return 'Europe/Kyiv';
  return tz;
};

export const getBrowserTimezone = (): string => {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return normalizeTimezone(tz);
  } catch {
    return 'UTC';
  }
};

export const getTimezoneOffsetString = (timeZone: string, date: Date = new Date()): string => {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: normalizeTimezone(timeZone),
      timeZoneName: 'longOffset',
    }).formatToParts(date);
    const tzPart = parts.find((p) => p.type === 'timeZoneName');
    if (tzPart && tzPart.value) {
      const val = tzPart.value.replace(/^GMT/, 'UTC');
      if (val === 'UTC') return 'UTC+00:00';
      return val;
    }
  } catch {
    // fallback if longOffset or invalid tz
  }
  return 'UTC+00:00';
};

export const formatTimezoneDisplay = (timeZone: string, date: Date = new Date()): string => {
  const normalized = normalizeTimezone(timeZone);
  const offset = getTimezoneOffsetString(normalized, date);
  return `${normalized} (${offset})`;
};
