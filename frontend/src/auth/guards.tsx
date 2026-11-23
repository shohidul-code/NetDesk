import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import type { Role } from "@/api/types";
import { NoAccessPage } from "@/pages/NoAccessPage";
import { homeFor, isRole } from "./roles";
import { useAuth } from "./useAuth";

function FullPageSpinner() {
  return (
    <div className="flex min-h-dvh items-center justify-center" aria-busy="true" aria-label="Loading">
      <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
    </div>
  );
}

/** Signed-in routes. The backend still enforces every rule; this only routes. */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "signed-out") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

/** A route for some roles only: other roles see "No access". */
export function RequireRole({ roles, children }: { roles: readonly Role[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user || !isRole(user.role, roles)) return <NoAccessPage />;
  return children;
}

/** Login and Claim: a signed-in user goes to their home instead. */
export function PublicOnly() {
  const { status, user } = useAuth();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "signed-in" && user) return <Navigate to={homeFor(user.role)} replace />;
  return <Outlet />;
}

export function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}
