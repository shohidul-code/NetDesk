import assert from "node:assert/strict";
import { test } from "node:test";
import { hoursOpen } from "./hours.ts";

const created = "2026-11-23T10:00:00Z";
const now = Date.parse("2026-11-24T14:30:00Z");

test("an open complaint counts up to now, in whole hours", () => {
  assert.equal(hoursOpen(created, "open", created, now), 28);
});

test("a resolved complaint stops at its last update", () => {
  assert.equal(hoursOpen(created, "resolved", "2026-11-23T13:59:00Z", now), 3);
});

test("never negative", () => {
  assert.equal(hoursOpen("2026-11-25T00:00:00Z", "open", created, now), 0);
});
