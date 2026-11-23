/**
 * One typed error for every failed API call (RULES.md §5.3), built from the envelope
 * {"error": {"code", "message", "details", "request_id"}} (PROPOSAL §8.3).
 * Kept free of imports so Node's test runner can load it directly.
 */

export interface FieldIssue {
  field: string;
  message: string;
}

interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  details: unknown;
  requestId: string | null;
  retryAfter: number | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId: string | null;
  /** Seconds from the Retry-After header (429), when the API sent one. */
  readonly retryAfter: number | null;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.details = init.details;
    this.requestId = init.requestId;
    this.retryAfter = init.retryAfter;
  }
}

interface HeaderReader {
  get(name: string): string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function toApiError(status: number, body: unknown, headers: HeaderReader): ApiError {
  const retry = Number(headers.get("retry-after"));
  const retryAfter = Number.isFinite(retry) && retry > 0 ? retry : null;
  const envelope = isRecord(body) && isRecord(body.error) ? body.error : null;
  if (!envelope) {
    // Not our envelope (a proxy page, an empty body): never show it to the user.
    return new ApiError({ status, code: `http_${status}`, message: "", details: null, requestId: null, retryAfter });
  }
  return new ApiError({
    status,
    code: typeof envelope.code === "string" ? envelope.code : `http_${status}`,
    message: typeof envelope.message === "string" ? envelope.message : "",
    details: envelope.details ?? null,
    requestId: typeof envelope.request_id === "string" ? envelope.request_id : null,
    retryAfter,
  });
}

/** A failed fetch (offline, DNS, CORS): status 0. */
export function networkError(): ApiError {
  return new ApiError({ status: 0, code: "network_error", message: "", details: null, requestId: null, retryAfter: null });
}

/** 422 details -> { field: message }, for messages under the inputs. */
export function fieldErrors(err: ApiError): Record<string, string> {
  if (err.status !== 422 || !Array.isArray(err.details)) return {};
  const out: Record<string, string> = {};
  for (const item of err.details as unknown[]) {
    if (isRecord(item) && typeof item.field === "string" && typeof item.message === "string") {
      out[item.field] ??= item.message;
    }
  }
  return out;
}

/** Plain words for the user (UI.md §8). 409 and 404 keep the server's own sentence. */
export function friendlyMessage(err: ApiError): string {
  switch (err.status) {
    case 401:
      return "Your session has ended. Please sign in again.";
    case 403:
      return "No access. Your account cannot do this.";
    case 404:
      return err.message || "We could not find that.";
    case 409:
      return err.message || "This conflicts with existing data.";
    case 422:
      return "Some fields need fixing. Check the messages under the inputs.";
    case 429:
      return "Too many attempts. Wait a little and try again.";
    case 503:
      return "The assistant is temporarily offline. Try again in a moment.";
    default:
      return "Something went wrong. Please try again.";
  }
}
