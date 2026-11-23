/** The only formatters for money and dates (RULES.md §5.9; formats from UI.md §9). */

// en-IN groups by lakh (1,50,000), the way amounts are written in Bangladesh.
const wholeTaka = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const withPaisa = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const monthFmt = new Intl.DateTimeFormat("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
const dateFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  timeZone: "Asia/Dhaka",
});

/** "1200.00" -> "৳1,200", "800.50" -> "৳800.50"; the API sends money as a decimal string. */
export function formatMoney(amount: string | number): string {
  const n = typeof amount === "string" ? Number(amount) : amount;
  return `৳${(Number.isInteger(n) ? wholeTaka : withPaisa).format(n)}`;
}

/** "2026-10" -> "Oct 2026". */
export function formatMonth(period: string): string {
  return monthFmt.format(new Date(`${period}-01T00:00:00Z`));
}

/** "2026-12-10" -> "10 Dec 2026". Read and printed in UTC, so the day never shifts. */
export function formatDate(isoDate: string): string {
  return dateFmt.format(new Date(`${isoDate.slice(0, 10)}T00:00:00Z`));
}

/** An instant, shown in Dhaka time: "24 Nov 2026, 2:30 am". */
export function formatDateTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso)).replace(" at ", ", ");
}
