import type { Role } from "@/api/types";

/** Where each role lands after sign-in (FRONTEND_AGENT_BRIEF "Route guard"). */
export function homeFor(role: string): string {
  if (role === "admin") return "/connections";
  if (role === "technician") return "/queue";
  return "/home";
}

export interface NavItem {
  to: string;
  label: string;
}

/** The menu comes from me.role (UI.md §3). Profile is in the header for everyone. */
export function navFor(role: string): NavItem[] {
  const assistant = { to: "/assistant", label: "Assistant" };
  if (role === "admin")
    return [
      { to: "/connections", label: "Connections" },
      { to: "/bills", label: "Bills" },
      { to: "/notices", label: "Notices" },
      { to: "/queue", label: "Complaints" },
      assistant,
    ];
  if (role === "technician")
    return [{ to: "/queue", label: "Complaints" }, { to: "/connections", label: "Connections" }, assistant];
  return [{ to: "/home", label: "Home" }, assistant, { to: "/complaints", label: "Complaints" }];
}

export function isRole(role: string, allowed: readonly Role[]): boolean {
  return (allowed as readonly string[]).includes(role);
}
