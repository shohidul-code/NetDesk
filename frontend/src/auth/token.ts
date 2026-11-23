/**
 * The access token, in memory and in localStorage so a page refresh keeps the session
 * (FRONTEND_AGENT_BRIEF "Auth handling"). Storage can be blocked, so every access is guarded.
 */
const KEY = "netdesk.token";
let current: string | null = null;

export function getToken(): string | null {
  if (current) return current;
  try {
    current = localStorage.getItem(KEY);
  } catch {
    current = null;
  }
  return current;
}

export function setToken(token: string): void {
  current = token;
  try {
    localStorage.setItem(KEY, token);
  } catch {
    // Private mode or blocked storage: the session lasts until the tab closes.
  }
}

export function clearToken(): void {
  current = null;
  try {
    localStorage.removeItem(KEY);
  } catch {
    // Nothing stored.
  }
}
