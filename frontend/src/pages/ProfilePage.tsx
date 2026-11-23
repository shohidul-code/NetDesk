import { useAuth } from "@/auth/useAuth";
import { PageHeader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const ROLE_LABEL: Record<string, string> = { admin: "Admin", technician: "Technician", customer: "Customer" };

export function ProfilePage() {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <>
      <PageHeader title="Profile" />
      <Card className="max-w-md">
        <CardContent className="space-y-3">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
            <dt className="text-text-muted">Name</dt>
            <dd>{user.full_name}</dd>
            <dt className="text-text-muted">Email</dt>
            <dd className="break-all">{user.email}</dd>
            <dt className="text-text-muted">Role</dt>
            <dd>{ROLE_LABEL[user.role] ?? user.role}</dd>
          </dl>
          <Button variant="outline" onClick={logout}>
            Sign out
          </Button>
        </CardContent>
      </Card>
    </>
  );
}
