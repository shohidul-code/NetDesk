/**
 * The only place that calls fetch (RULES.md §5.2). Adds the token, parses the error
 * envelope into ApiError, and on a 401 for a signed-in call clears the session.
 */
import { clearToken, getToken } from "@/auth/token";
import { ApiError, networkError, toApiError } from "./errors";

const BASE = `${(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")}/api/v1`;

let onUnauthorized: () => void = () => undefined;

/** The auth provider registers how to sign out when the API says the session is over. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

export type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  query?: Query;
  json?: unknown;
  form?: Record<string, string>;
}

function url(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: string | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(options.form).toString();
  }

  let response: Response;
  try {
    response = await fetch(url(path, options.query), { method: options.method ?? "GET", headers, body });
  } catch {
    throw networkError();
  }
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (response.ok) return data as T;

  const error = toApiError(response.status, data, response.headers);
  if (error.status === 401 && token) {
    clearToken();
    onUnauthorized();
  }
  throw error;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>(path, { query }),
  post: <T>(path: string, json?: unknown) => request<T>(path, { method: "POST", json }),
  patch: <T>(path: string, json: unknown) => request<T>(path, { method: "PATCH", json }),
  delete: (path: string) => request<undefined>(path, { method: "DELETE" }),
};

export { ApiError };
