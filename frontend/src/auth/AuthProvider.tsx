import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, request, setUnauthorizedHandler } from "@/api/client";
import type { Schemas, User } from "@/api/types";
import { AuthContext, type AuthState } from "./context";
import { clearToken, getToken, setToken } from "./token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>(() => (getToken() ? "loading" : "signed-out"));

  const logout = useCallback(() => {
    clearToken();
    queryClient.clear();
    setUser(null);
    setStatus("signed-out");
  }, [queryClient]);

  useEffect(() => {
    // Any 401 on a signed-in call ends the session; the route guard then shows Login.
    setUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    if (!getToken()) return;
    let cancelled = false;
    api
      .get<User>("/auth/me")
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus("signed-in");
      })
      .catch(() => {
        if (cancelled) return;
        clearToken();
        setStatus("signed-out");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // OAuth2 password form; the API gives the same 401 for any wrong email or password.
    const token = await request<Schemas["Token"]>("/auth/login", {
      method: "POST",
      form: { username: email, password },
    });
    setToken(token.access_token);
    const me = await api.get<User>("/auth/me");
    setUser(me);
    setStatus("signed-in");
    return me;
  }, []);

  const value = useMemo(() => ({ status, user, login, logout }), [status, user, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
