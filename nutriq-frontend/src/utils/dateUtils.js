/**
 * NutriQ Centralized Date & Timezone Utility
 * 
 * Provides timezone-safe, pure-calendar date arithmetic and formatting.
 * Guaranteed to never shift dates due to UTC conversions (e.g. UTC+05:30 IST).
 */

const DEFAULT_TIMEZONE = 'Asia/Kolkata';

/**
 * Returns today's calendar date in YYYY-MM-DD string format for the user's timezone.
 */
export const getToday = (timeZone = DEFAULT_TIMEZONE) => {
  try {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
    return formatter.format(new Date());
  } catch (e) {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
};

/**
 * Parses YYYY-MM-DD into year, month, day numbers.
 */
export const parseDateParts = (dateStr) => {
  if (!dateStr || typeof dateStr !== 'string') {
    const todayStr = getToday();
    const [y, m, d] = todayStr.split('-').map(Number);
    return { year: y, month: m, day: d };
  }
  const clean = dateStr.split('T')[0];
  const parts = clean.split('-').map(Number);
  if (parts.length === 3 && !isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
    return { year: parts[0], month: parts[1], day: parts[2] };
  }
  const todayStr = getToday();
  const [y, m, d] = todayStr.split('-').map(Number);
  return { year: y, month: m, day: d };
};

/**
 * Adds exactly n calendar days to a YYYY-MM-DD string.
 * Uses local noon (12:00:00) to prevent any daylight saving / UTC boundary shifts.
 * 
 * Example:
 * addDays("2026-08-20", -1) -> "2026-08-19"
 * addDays("2026-08-19", -1) -> "2026-08-18"
 * addDays("2026-08-19", 1)  -> "2026-08-20"
 */
export const addDays = (dateStr, n = 1) => {
  const { year, month, day } = parseDateParts(dateStr);
  const d = new Date(year, month - 1, day + n, 12, 0, 0, 0);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dayNum = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dayNum}`;
};

/**
 * Subtracts exactly n calendar days from a YYYY-MM-DD string.
 */
export const subtractDays = (dateStr, n = 1) => {
  return addDays(dateStr, -n);
};

/**
 * Formats a YYYY-MM-DD date string into human readable display.
 * 
 * formatType = 'full'  -> "Thursday, August 20, 2026"
 * formatType = 'short' -> "20-Aug-2026"
 * formatType = 'month_day' -> "Aug 20, 2026"
 */
export const formatDate = (dateStr, formatType = 'full') => {
  if (!dateStr) return '';
  const { year, month, day } = parseDateParts(dateStr);
  const d = new Date(year, month - 1, day, 12, 0, 0, 0);
  if (isNaN(d.getTime())) return dateStr;

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const shortMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  if (formatType === 'short') {
    return `${String(day).padStart(2, '0')}-${shortMonths[month - 1]}-${year}`;
  }

  if (formatType === 'month_day') {
    return `${shortMonths[month - 1]} ${day}, ${year}`;
  }

  // default 'full'
  return `${dayNames[d.getDay()]}, ${monthNames[month - 1]} ${day}, ${year}`;
};

/**
 * Checks if a given date string represents today's date.
 */
export const isToday = (dateStr, timeZone = DEFAULT_TIMEZONE) => {
  if (!dateStr) return false;
  const target = dateStr.split('T')[0];
  const today = getToday(timeZone);
  return target === today;
};

/**
 * Checks if a given date string is in the future.
 */
export const isFuture = (dateStr, timeZone = DEFAULT_TIMEZONE) => {
  if (!dateStr) return false;
  const target = dateStr.split('T')[0];
  const today = getToday(timeZone);
  return target > today;
};

/**
 * Extracts YYYY-MM-DD from an ISO timestamp, SQLite string, or Date object
 * strictly evaluated in the specified timezone (Asia/Kolkata).
 */
export const getLocalDateFromTimestamp = (ts, timeZone = DEFAULT_TIMEZONE) => {
  if (!ts) return getToday(timeZone);
  try {
    let dateObj;
    if (ts instanceof Date) {
      dateObj = ts;
    } else if (typeof ts === 'string') {
      if (!ts.includes('Z') && !ts.includes('+') && ts.includes('T')) {
        dateObj = new Date(ts + 'Z');
      } else if (!ts.includes('T') && ts.includes(' ')) {
        dateObj = new Date(ts.replace(' ', 'T') + 'Z');
      } else {
        dateObj = new Date(ts);
      }
    } else {
      dateObj = new Date(ts);
    }

    if (isNaN(dateObj.getTime())) {
      return String(ts).split('T')[0].split(' ')[0];
    }

    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
    return formatter.format(dateObj);
  } catch (e) {
    return String(ts).split('T')[0].split(' ')[0];
  }
};

/**
 * Universal getLocalDate helper accepting timestamp, Date object, or YYYY-MM-DD string
 */
export const getLocalDate = (ts, timeZone = DEFAULT_TIMEZONE) => {
  return getLocalDateFromTimestamp(ts, timeZone);
};

/**
 * Formats timestamp to 12-hour local time (e.g. "08:30 AM") in user timezone.
 */
export const formatTime = (ts, timeZone = DEFAULT_TIMEZONE) => {
  if (!ts) return '';
  try {
    let dateObj;
    if (ts instanceof Date) {
      dateObj = ts;
    } else if (typeof ts === 'string') {
      if (!ts.includes('Z') && !ts.includes('+') && ts.includes('T')) {
        dateObj = new Date(ts + 'Z');
      } else if (!ts.includes('T') && ts.includes(' ')) {
        dateObj = new Date(ts.replace(' ', 'T') + 'Z');
      } else {
        dateObj = new Date(ts);
      }
    } else {
      dateObj = new Date(ts);
    }

    if (isNaN(dateObj.getTime())) return '';

    return dateObj.toLocaleTimeString('en-US', {
      timeZone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  } catch (e) {
    return '';
  }
};

/**
 * Generates ISO string start of day (00:00:00.000 local) in UTC.
 */
export const getStartOfDay = (dateStr, timeZone = DEFAULT_TIMEZONE) => {
  const { year, month, day } = parseDateParts(dateStr);
  // In Asia/Kolkata (+05:30), 00:00:00 IST is previous day 18:30:00 UTC
  // Using pure offset math for IST (+330 minutes)
  const localUtcMs = Date.UTC(year, month - 1, day, 0, 0, 0, 0) - (5.5 * 3600 * 1000);
  return new Date(localUtcMs).toISOString();
};

/**
 * Generates ISO string end of day (23:59:59.999 local) in UTC.
 */
export const getEndOfDay = (dateStr, timeZone = DEFAULT_TIMEZONE) => {
  const { year, month, day } = parseDateParts(dateStr);
  const localUtcMs = Date.UTC(year, month - 1, day, 23, 59, 59, 999) - (5.5 * 3600 * 1000);
  return new Date(localUtcMs).toISOString();
};
