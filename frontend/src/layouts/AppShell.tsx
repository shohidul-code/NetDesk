/**
 * The signed-in frame (UI.md §3): staff get a left sidebar from 640px and a menu sheet
 * below it; customers get top links from 640px and a bottom bar below it.
 */
import { Menu, UserRound } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router";
import { navFor } from "@/auth/roles";
import { useAuth } from "@/auth/useAuth";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex min-h-11 items-center rounded-md px-3 text-sm font-medium",
    isActive ? "bg-primary/10 text-primary" : "text-text hover:bg-bg",
  );

export function AppShell() {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  if (!user) return null;
  const items = navFor(user.role);
  const isCustomer = user.role === "customer";

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 border-b border-border bg-surface">
        <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-3 px-4">
          {!isCustomer && (
            <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="sm:hidden" aria-label="Open menu">
                  <Menu />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64">
                <SheetHeader>
                  <SheetTitle>NetDesk</SheetTitle>
                </SheetHeader>
                <nav className="flex flex-col gap-1 px-2" aria-label="Main">
                  {items.map((item) => (
                    <NavLink key={item.to} to={item.to} className={linkClass} onClick={() => setMenuOpen(false)}>
                      {item.label}
                    </NavLink>
                  ))}
                </nav>
              </SheetContent>
            </Sheet>
          )}
          <Link to="/" className="text-lg font-semibold text-primary">
            NetDesk
          </Link>
          {isCustomer && (
            <nav className="ml-4 hidden gap-1 sm:flex" aria-label="Main">
              {items.map((item) => (
                <NavLink key={item.to} to={item.to} className={linkClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
          )}
          <NavLink
            to="/profile"
            className={(s) => cn(linkClass(s), "ml-auto gap-2")}
            aria-label={`Profile of ${user.full_name}`}
          >
            <UserRound className="size-5" aria-hidden />
            <span className="hidden sm:inline">{user.full_name}</span>
          </NavLink>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1200px]">
        {!isCustomer && (
          <nav className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-56 shrink-0 flex-col gap-1 border-r border-border p-3 sm:flex" aria-label="Main">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
        <main className={cn("min-w-0 flex-1 p-4 sm:p-6", isCustomer && "pb-24 sm:pb-6")}>
          <Outlet />
        </main>
      </div>

      {isCustomer && (
        <nav
          className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-border bg-surface sm:hidden"
          aria-label="Main"
        >
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn("flex min-h-14 items-center justify-center text-sm font-medium", isActive ? "text-primary" : "text-text-muted")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
