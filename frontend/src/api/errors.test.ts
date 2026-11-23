import assert from "node:assert/strict";
import { test } from "node:test";
import { ApiError, fieldErrors, friendlyMessage, toApiError } from "./errors.ts";

const headers = (h: Record<string, string> = {}) => ({ get: (n: string) => h[n.toLowerCase()] ?? null });

test("the error envelope becomes one typed error", () => {
  const err = toApiError(
    409,
    { error: { code: "conflict", message: "TrxID already used.", details: null, request_id: "abc123" } },
    headers({ "retry-after": "60" }),
  );
  assert.ok(err instanceof ApiError);
  assert.equal(err.status, 409);
  assert.equal(err.code, "conflict");
  assert.equal(err.message, "TrxID already used.");
  assert.equal(err.requestId, "abc123");
  assert.equal(err.retryAfter, 60);
});

test("a body that is not our envelope still gives a safe error", () => {
  const err = toApiError(502, "<html>Bad gateway</html>", headers());
  assert.equal(err.code, "http_502");
  assert.equal(err.requestId, null);
  assert.doesNotMatch(friendlyMessage(err), /html|502/i);
});

test("422 details become a field -> message map", () => {
  const err = toApiError(
    422,
    { error: { code: "validation_error", message: "Some fields are invalid.", request_id: "r",
      details: [{ field: "phone", message: "Not a Bangladeshi mobile number" }] } },
    headers(),
  );
  assert.deepEqual(fieldErrors(err), { phone: "Not a Bangladeshi mobile number" });
});

test("friendly text by status; 409 keeps the server's own message", () => {
  const make = (status: number, code = "x", message = "Server says no.") =>
    new ApiError({ status, code, message, details: null, requestId: null, retryAfter: null });
  assert.match(friendlyMessage(make(503)), /temporarily offline/);
  assert.match(friendlyMessage(make(0, "network_error")), /Something went wrong/);
  assert.equal(friendlyMessage(make(409)), "Server says no.");
  assert.match(friendlyMessage(make(403)), /No access/);
});
