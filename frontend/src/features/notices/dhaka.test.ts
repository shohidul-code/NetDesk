import assert from "node:assert/strict";
import { test } from "node:test";
import { currentPeriod, dhakaLocalFromNow, dhakaLocalToIso, isoToDhakaLocal, noticeState } from "./dhaka.ts";

test("a datetime-local value is sent as Dhaka time", () => {
  assert.equal(dhakaLocalToIso("2026-11-24T09:30"), "2026-11-24T09:30:00+06:00");
  assert.equal(dhakaLocalToIso("2026-11-24T09:30:15"), "2026-11-24T09:30:15+06:00");
});

test("an instant shows in Dhaka time and round-trips", () => {
  assert.equal(isoToDhakaLocal("2026-11-24T03:30:00Z"), "2026-11-24T09:30");
  assert.equal(Date.parse(dhakaLocalToIso(isoToDhakaLocal("2026-11-24T03:30:00Z"))), Date.parse("2026-11-24T03:30:00Z"));
  assert.equal(isoToDhakaLocal("2026-11-24T20:00:00Z"), "2026-11-25T02:00"); // crosses midnight
});

test("defaults and the current month use Dhaka time", () => {
  const now = Date.parse("2026-11-30T20:00:00Z"); // already 1 Dec in Dhaka
  assert.equal(currentPeriod(now), "2026-12");
  assert.equal(dhakaLocalFromNow(2, now), "2026-12-01T04:00");
});

test("notice state from its window", () => {
  const now = Date.parse("2026-11-24T12:00:00Z");
  assert.equal(noticeState("2026-11-24T13:00:00Z", "2026-11-24T14:00:00Z", now), "upcoming");
  assert.equal(noticeState("2026-11-24T11:00:00Z", "2026-11-24T14:00:00Z", now), "active");
  assert.equal(noticeState("2026-11-24T10:00:00Z", "2026-11-24T12:00:00Z", now), "ended");
});
