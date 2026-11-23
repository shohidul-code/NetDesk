import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDate, formatDateTime, formatMonth, formatMoney } from "./format.ts";

test("money: taka sign, grouping, no .00, keeps paisa", () => {
  assert.equal(formatMoney("1200.00"), "৳1,200");
  assert.equal(formatMoney("150000.00"), "৳1,50,000"); // lakh grouping, as in Bangladesh
  assert.equal(formatMoney("800.50"), "৳800.50");
  assert.equal(formatMoney(0), "৳0");
});

test("month and date in UI.md style", () => {
  assert.equal(formatMonth("2026-10"), "Oct 2026");
  assert.equal(formatMonth("2026-09"), "Sep 2026"); // not the newer CLDR "Sept"
  assert.equal(formatDate("2026-12-10"), "10 Dec 2026"); // a date-only value never shifts a day
  assert.equal(formatDate("2026-09-05"), "5 Sep 2026");
});

test("date-time is shown in Asia/Dhaka (UTC+6)", () => {
  assert.equal(formatDateTime("2026-11-23T20:30:00Z"), "24 Nov 2026, 2:30 am");
});
