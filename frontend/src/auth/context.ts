import { createContext } from "react";
import type { User } from "@/api/types";

export interface AuthState {
  /** "loading" while a stored token is checked with /auth/me on start. */
  status: "loading" | "signed-out" | "signed-in";
  user: User | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState | null>(null);
