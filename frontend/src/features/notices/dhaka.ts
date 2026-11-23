/**
 * Bangladesh time is a fixed UTC+6 (no daylight saving), so Dhaka conversions are plain arithmetic.
 * A <input type="datetime-local"> holds "YYYY-MM-DDTHH:mm" with no zone; we read it as Dhaka time
 * and send the API an ISO string with +06:00, so the instant does not depend on the browser's zone.
 */
const DHAKA_OFFSET_MS = 6 * 3_600_000;

export function dhakaLocalToIso(local: string): string {
  return `${local.length === 16 ? `${local}:00` : local}+06:00`;
}

/** An instant -> the "YYYY-MM-DDTHH:mm" a datetime-local input shows, in Dhaka time. */
export function isoToDhakaLocal(iso: string): string {
  return new Date(Date.parse(iso) + DHAKA_OFFSET_MS).toISOString().slice(0, 16);
}

/** Now plus `hours`, as a Dhaka datetime-local value (default form values). */
export function dhakaLocalFromNow(hours = 0, now = Date.now()): string {
  return isoToDhakaLocal(new Date(now + hours * 3_600_000).toISOString());
}

/** The current month in Dhaka as "YYYY-MM" (default for the bill month). */
export function currentPeriod(now = Date.now()): string {
  return new Date(now + DHAKA_OFFSET_MS).toISOString().slice(0, 7);
}

export type NoticeState = "upcoming" | "active" | "ended";

export function noticeState(startsAt: string, endsAt: string, now = Date.now()): NoticeState {
  if (now < Date.parse(startsAt)) return "upcoming";
  return now < Date.parse(endsAt) ? "active" : "ended";
}
