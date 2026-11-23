import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";
import { ApiError, fieldErrors } from "@/api/errors";
import { homeFor } from "@/auth/roles";
import { useAuth } from "@/auth/useAuth";
import { FormError } from "@/components/states";
import { PasswordInput } from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRegister } from "@/features/claim/useRegister";

const schema = z.object({
  customer_code: z.string().trim().min(1, "Enter your customer code."),
  phone: z.string().trim().min(1, "Enter your phone number."),
  email: z.email("Enter a valid email address."),
  password: z.string().min(10, "Use at least 10 characters."),
});
type Values = z.infer<typeof schema>;
const FIELDS: (keyof Values)[] = ["customer_code", "phone", "email", "password"];

export function ClaimPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const register = useRegister();
  const [error, setError] = useState<unknown>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { customer_code: "", phone: "", email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      await register.mutateAsync({ ...values, customer_code: values.customer_code.toUpperCase() });
      const me = await login(values.email, values.password);
      navigate(homeFor(me.role), { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        // Keep what the user typed; show the server's message under each input.
        for (const [field, message] of Object.entries(fieldErrors(e))) {
          if ((FIELDS as string[]).includes(field)) form.setError(field as keyof Values, { message });
        }
      }
      setError(e);
    }
  });

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl text-primary">Claim your account</CardTitle>
          <p className="text-sm text-text-muted">
            Use the customer code and phone number your operator gave you. This links your connection to a login.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="customer_code">Customer code</Label>
              <Input id="customer_code" placeholder="ND-000001" autoComplete="off" aria-invalid={!!errors.customer_code} {...form.register("customer_code")} />
              {errors.customer_code && <p className="text-sm text-danger">{errors.customer_code.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" type="tel" autoComplete="tel" aria-invalid={!!errors.phone} {...form.register("phone")} />
              {errors.phone && <p className="text-sm text-danger">{errors.phone.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...form.register("email")} />
              {errors.email && <p className="text-sm text-danger">{errors.email.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <PasswordInput id="password" autoComplete="new-password" aria-invalid={!!errors.password} {...form.register("password")} />
              {errors.password ? (
                <p className="text-sm text-danger">{errors.password.message}</p>
              ) : (
                <p className="text-sm text-text-muted">At least 10 characters.</p>
              )}
            </div>
            <ClaimError error={error} />
            <Button type="submit" className="h-11 w-full" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
              Claim account
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-text-muted">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

/** 404, 429 and 409 have set wording (UI.md §6.2); 422 is already shown under the inputs. */
function ClaimError({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) return <FormError error={error} />;
  if (error.status === 404)
    return (
      <p role="alert" className="text-sm text-danger">
        We could not find a connection with this code and phone. Check them or call your operator.
      </p>
    );
  if (error.status === 429)
    return (
      <p role="alert" className="text-sm text-danger">
        Too many attempts. Wait a little and try again.
      </p>
    );
  return <FormError error={error} />;
}
