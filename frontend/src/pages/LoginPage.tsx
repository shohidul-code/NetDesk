import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router";
import { z } from "zod";
import { ApiError } from "@/api/errors";
import { homeFor } from "@/auth/roles";
import { useAuth } from "@/auth/useAuth";
import { PasswordInput } from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});
type Values = z.infer<typeof schema>;

/** The API gives one 401 for any wrong email or password, so the UI does too (UI.md §6.1). */
function loginMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) return "Incorrect email or password.";
  if (error instanceof ApiError && error.status === 429) return "Too many attempts. Wait a little and try again.";
  return "Something went wrong. Please try again.";
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from;
  const [error, setError] = useState<unknown>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async ({ email, password }) => {
    setError(null);
    try {
      const me = await login(email, password);
      navigate(from && from !== "/" ? from : homeFor(me.role), { replace: true });
    } catch (e) {
      setError(e);
    }
  });

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl text-primary">NetDesk</CardTitle>
          <p className="text-sm text-text-muted">Your bills, outages and help, in Bangla or English.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...form.register("email")} />
              {errors.email && <p className="text-sm text-danger">{errors.email.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <PasswordInput id="password" autoComplete="current-password" aria-invalid={!!errors.password} {...form.register("password")} />
              {errors.password && <p className="text-sm text-danger">{errors.password.message}</p>}
            </div>
            {error !== null && (
              <p role="alert" className="text-sm text-danger">
                {loginMessage(error)}
              </p>
            )}
            <Button type="submit" className="h-11 w-full" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
              Sign in
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-text-muted">
            New customer?{" "}
            <Link to="/claim" className="font-medium text-primary underline-offset-4 hover:underline">
              Claim your account
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
