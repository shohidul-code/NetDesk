import { createBrowserRouter } from "react-router";
import { HomeRedirect, PublicOnly, RequireAuth, RequireRole } from "@/auth/guards";
import { AppShell } from "@/layouts/AppShell";
import { AssistantPage } from "@/pages/AssistantPage";
import { BillsPage } from "@/pages/BillsPage";
import { ClaimPage } from "@/pages/ClaimPage";
import { ConnectionsPage } from "@/pages/ConnectionsPage";
import { CustomerHomePage } from "@/pages/CustomerHomePage";
import { LoginPage } from "@/pages/LoginPage";
import { MyComplaintsPage } from "@/pages/MyComplaintsPage";
import { NoticesPage } from "@/pages/NoticesPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { TechnicianQueuePage } from "@/pages/TechnicianQueuePage";

/** Route -> page -> roles. The 9 P0 pages plus Profile (UI.md §4). */
export const router = createBrowserRouter([
  {
    element: <PublicOnly />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/claim", element: <ClaimPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <HomeRedirect /> },
          { path: "/home", element: <RequireRole roles={["customer"]}><CustomerHomePage /></RequireRole> },
          { path: "/complaints", element: <RequireRole roles={["customer"]}><MyComplaintsPage /></RequireRole> },
          { path: "/assistant", element: <AssistantPage /> },
          { path: "/queue", element: <RequireRole roles={["technician", "admin"]}><TechnicianQueuePage /></RequireRole> },
          { path: "/connections", element: <RequireRole roles={["technician", "admin"]}><ConnectionsPage /></RequireRole> },
          { path: "/bills", element: <RequireRole roles={["admin"]}><BillsPage /></RequireRole> },
          { path: "/notices", element: <RequireRole roles={["admin"]}><NoticesPage /></RequireRole> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
